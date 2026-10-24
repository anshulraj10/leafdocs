import os
import pathlib
import hashlib
import re
import secrets

import bcrypt
import frontmatter
import markdown
import nh3
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

load_dotenv()


def _load_pins() -> list[bytes]:
    """Read LEAFDOCS_PINS from env, hash each with bcrypt, return list of hashes."""
    raw = os.getenv("LEAFDOCS_PINS", "").strip()
    if not raw:
        return []
    pins = [p.strip() for p in raw.split(",") if p.strip()]
    return [bcrypt.hashpw(p.encode(), bcrypt.gensalt()) for p in pins]


def _verify_pin(candidate: str, hashes: list[bytes]) -> bool:
    return any(bcrypt.checkpw(candidate.encode(), h) for h in hashes)


_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "toc", "nl2br", "pymdownx.arithmatex"]
# Generic mode emits plain span/div.arithmatex wrappers for a client-side renderer (KaTeX).
# Inline math is \(...\) only, so single dollar signs in prose (prices) stay plain text.
_MARKDOWN_EXTENSION_CONFIGS = {"pymdownx.arithmatex": {"generic": True, "inline_syntax": ["round"]}}

# Everything the enabled Markdown extensions (fenced_code, tables, toc, nl2br, arithmatex) emit
_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "ul", "ol", "li", "blockquote", "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td",
    "em", "strong", "del", "a", "img", "div", "span",
}
_ALLOWED_ATTRIBUTES = {
    **{h: {"id"} for h in ("h1", "h2", "h3", "h4", "h5", "h6")},
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
    "div": {"class"},
    "span": {"class"},
    "th": {"style"},
    "td": {"style"},
}
_LANGUAGE_CLASS = re.compile(r"language-[\w+#.-]+")


def _filter_attribute(tag: str, attr: str, value: str) -> str | None:
    """Restrict class values to what fenced_code (language-*), toc (toc) and arithmatex produce."""
    if attr == "class":
        if tag == "code" and _LANGUAGE_CLASS.fullmatch(value):
            return value
        if tag == "div" and value in ("toc", "arithmatex"):
            return value
        if tag == "span" and value == "arithmatex":
            return value
        return None
    return value


def _sanitize(html: str) -> str:
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        attribute_filter=_filter_attribute,
        filter_style_properties={"text-align"},
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Top-level slugs that would collide with built-in routes
_RESERVED_SLUGS = {"login", "logout"}


def _slug(filepath: pathlib.Path, docs_dir: pathlib.Path) -> str:
    """Convert a .md filepath to its URL slug (posix path relative to docs_dir, no .md)."""
    return filepath.relative_to(docs_dir).with_suffix("").as_posix()


def _display_name(name: str) -> str:
    """Titlecase a file stem or directory name, treating - and _ as spaces."""
    return name.replace("-", " ").replace("_", " ").title()


def _doc_meta(post: frontmatter.Post, md_file: pathlib.Path) -> tuple[str, list[str]]:
    """Return (title, tags) from frontmatter, falling back to the filename for title."""
    title = post.get("title") or _display_name(md_file.stem)
    tags = post.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return title, tags


def _is_hidden(rel: pathlib.PurePath) -> bool:
    return any(part.startswith(".") for part in rel.parts)


def _is_reserved(slug: str) -> bool:
    return slug in _RESERVED_SLUGS or slug.startswith("static/")


def _is_inside(path: pathlib.Path, docs_dir: pathlib.Path) -> bool:
    """True if path, with symlinks resolved, is still inside docs_dir."""
    try:
        path.resolve().relative_to(docs_dir)
    except ValueError:
        return False
    return True


def _discover_docs(docs_dir: pathlib.Path) -> list[dict]:
    """
    Recursively scan docs_dir for .md files. Return list of dicts with:
      slug, title, tags, path
    Sorted alphabetically by title. Hidden paths, symlinks that escape
    docs_dir, and reserved slugs are skipped.
    """
    docs = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        if _is_hidden(md_file.relative_to(docs_dir)):
            continue
        if not md_file.is_file() or not _is_inside(md_file, docs_dir):
            continue
        slug = _slug(md_file, docs_dir)
        if _is_reserved(slug):
            continue
        post = frontmatter.load(str(md_file))
        title, tags = _doc_meta(post, md_file)
        docs.append(
            {
                "slug": slug,
                "title": title,
                "tags": tags,
                "path": md_file,
            }
        )
    docs.sort(key=lambda d: d["title"].lower())
    return docs


def _build_tree(docs: list[dict]) -> dict:
    """
    Group docs into nested folders by slug. Each node has:
      name, title, folders, docs
    Folders come sorted by name and docs by title, both case-insensitive.
    Only folders that hold docs somewhere beneath them exist.
    """
    def new_node(name: str) -> dict:
        return {"name": name, "title": _display_name(name), "folders": {}, "docs": []}

    root = new_node("")
    for doc in docs:
        node = root
        for part in doc["slug"].split("/")[:-1]:
            node = node["folders"].setdefault(part, new_node(part))
        node["docs"].append(doc)

    def finish(node: dict) -> dict:
        node["folders"] = [finish(f) for f in sorted(node["folders"].values(), key=lambda f: f["name"].lower())]
        node["docs"].sort(key=lambda d: d["title"].lower())
        return node

    return finish(root)


class LeafDocs:
    def __init__(
        self,
        docs_dir: str = "./docs",
        secret_key: str | None = None,
    ):
        self.docs_dir = pathlib.Path(docs_dir).resolve()
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"docs_dir not found: {self.docs_dir}")

        self._pin_hashes = _load_pins()
        self._auth_enabled = bool(self._pin_hashes)

        self.flask_app = Flask(__name__)
        self.flask_app.secret_key = secret_key or os.getenv("LEAFDOCS_SECRET_KEY") or secrets.token_hex(32)

        # Secure by default; only an explicit false-like value disables it (plain HTTP setups)
        cookie_secure = os.getenv("LEAFDOCS_COOKIE_SECURE", "").strip().lower() not in ("false", "0", "no", "off")
        self.flask_app.config.update(
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SECURE=cookie_secure,
            SESSION_COOKIE_SAMESITE="Lax",
        )

        # Off by default; raw HTML in docs is only safe when every author is trusted
        self._allow_html = os.getenv("LEAFDOCS_ALLOW_HTML", "").strip().lower() in ("true", "1", "yes", "on")

        self._register_routes()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_authenticated(self) -> bool:
        if not self._auth_enabled:
            return True
        return session.get("authenticated") is True

    def _require_auth(self):
        if not self._is_authenticated():
            return redirect(url_for("login"))
        return None

    def _serve_image(self, slug: str):
        """Serve an image file from docs_dir. Caller has already checked auth."""
        rel = pathlib.PurePosixPath(slug)
        if _is_hidden(rel):
            abort(404)
        image = self.docs_dir / rel
        if not image.is_file():
            abort(404)
        if not _is_inside(image, self.docs_dir):
            abort(403)
        return send_file(image.resolve())

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def _register_routes(self):
        app = self.flask_app

        # Attach self so inner functions can reference it
        leafdocs = self

        @app.route("/login", methods=["GET", "POST"])
        def login():
            if not leafdocs._auth_enabled:
                return redirect(url_for("index"))

            error = None
            if request.method == "POST":
                pin = request.form.get("pin", "")
                if _verify_pin(pin, leafdocs._pin_hashes):
                    session["authenticated"] = True
                    session.permanent = False
                    return redirect(url_for("index"))
                error = "Incorrect pin."

            return render_template("login.html", error=error)

        @app.route("/logout")
        def logout():
            session.clear()
            return redirect(url_for("login"))

        @app.route("/")
        def index():
            redir = leafdocs._require_auth()
            if redir:
                return redir
            docs = _discover_docs(leafdocs.docs_dir)
            return render_template(
                "index.html",
                docs=docs,
                tree=_build_tree(docs),
                auth_enabled=leafdocs._auth_enabled,
            )

        @app.route("/<path:slug>")
        def reader(slug: str):
            redir = leafdocs._require_auth()
            if redir:
                return redir

            # Old-style links to the .md file land on the doc itself
            if slug.endswith(".md"):
                if not slug[:-3]:
                    abort(404)
                return redirect(url_for("reader", slug=slug[:-3]))

            if pathlib.PurePosixPath(slug).suffix.lower() in _IMAGE_SUFFIXES:
                return leafdocs._serve_image(slug)

            rel = pathlib.PurePosixPath(f"{slug}.md")
            if _is_hidden(rel) or _is_reserved(rel.as_posix()[:-3]):
                abort(404)

            # Find matching file
            md_file = leafdocs.docs_dir / rel
            if not md_file.is_file():
                abort(404)

            # Security: ensure resolved path is still inside docs_dir
            if not _is_inside(md_file, leafdocs.docs_dir):
                abort(403)

            post = frontmatter.load(str(md_file))
            title, tags = _doc_meta(post, md_file)
            crumbs = [_display_name(part) for part in rel.parts[:-1]]

            html_content = markdown.markdown(
                post.content,
                extensions=_MARKDOWN_EXTENSIONS,
                extension_configs=_MARKDOWN_EXTENSION_CONFIGS,
            )
            if not leafdocs._allow_html:
                html_content = _sanitize(html_content)

            # Load the KaTeX and mermaid assets only on pages that need them. Match whole
            # opening tags: text like `class="arithmatex"` in a code span keeps its quotes,
            # but its < is always escaped, so it cannot match.
            has_math = '<span class="arithmatex">' in html_content or '<div class="arithmatex">' in html_content
            has_mermaid = '<code class="language-mermaid">' in html_content

            return render_template(
                "reader.html",
                title=title,
                tags=tags,
                crumbs=crumbs,
                content=html_content,
                has_math=has_math,
                has_mermaid=has_mermaid,
                auth_enabled=leafdocs._auth_enabled,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, host: str = "127.0.0.1", port: int = 5000, **kwargs):
        self.flask_app.run(host=host, port=port, **kwargs)
