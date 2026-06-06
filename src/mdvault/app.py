import os
import pathlib
import hashlib
import secrets

import bcrypt
import frontmatter
import markdown
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

load_dotenv()


def _load_pins() -> list[bytes]:
    """Read MDVAULT_PINS from env, hash each with bcrypt, return list of hashes."""
    raw = os.getenv("MDVAULT_PINS", "").strip()
    if not raw:
        return []
    pins = [p.strip() for p in raw.split(",") if p.strip()]
    return [bcrypt.hashpw(p.encode(), bcrypt.gensalt()) for p in pins]


def _verify_pin(candidate: str, hashes: list[bytes]) -> bool:
    return any(bcrypt.checkpw(candidate.encode(), h) for h in hashes)


def _slug(filepath: pathlib.Path) -> str:
    """Convert a .md filepath to its URL slug (stem only)."""
    return filepath.stem


def _discover_docs(docs_dir: pathlib.Path) -> list[dict]:
    """
    Scan docs_dir for .md files. Return list of dicts with:
      slug, title, tags, path
    Sorted alphabetically by title.
    """
    docs = []
    for md_file in sorted(docs_dir.glob("*.md")):
        post = frontmatter.load(str(md_file))
        title = post.get("title") or md_file.stem.replace("-", " ").replace("_", " ").title()
        tags = post.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        docs.append(
            {
                "slug": _slug(md_file),
                "title": title,
                "tags": tags,
                "path": md_file,
            }
        )
    docs.sort(key=lambda d: d["title"].lower())
    return docs


class MDVault:
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
        self.flask_app.secret_key = secret_key or os.getenv("MDVAULT_SECRET_KEY") or secrets.token_hex(32)

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

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def _register_routes(self):
        app = self.flask_app

        # Attach self so inner functions can reference it
        vault = self

        @app.route("/login", methods=["GET", "POST"])
        def login():
            if not vault._auth_enabled:
                return redirect(url_for("index"))

            error = None
            if request.method == "POST":
                pin = request.form.get("pin", "")
                if _verify_pin(pin, vault._pin_hashes):
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
            redir = vault._require_auth()
            if redir:
                return redir
            docs = _discover_docs(vault.docs_dir)
            return render_template("index.html", docs=docs, auth_enabled=vault._auth_enabled)

        @app.route("/<slug>")
        def reader(slug: str):
            redir = vault._require_auth()
            if redir:
                return redir

            # Find matching file
            md_file = vault.docs_dir / f"{slug}.md"
            if not md_file.exists():
                abort(404)

            # Security: ensure resolved path is still inside docs_dir
            try:
                md_file.resolve().relative_to(vault.docs_dir)
            except ValueError:
                abort(403)

            post = frontmatter.load(str(md_file))
            title = post.get("title") or md_file.stem.replace("-", " ").replace("_", " ").title()
            tags = post.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            html_content = markdown.markdown(
                post.content,
                extensions=["fenced_code", "tables", "toc", "nl2br"],
            )

            return render_template(
                "reader.html",
                title=title,
                tags=tags,
                content=html_content,
                auth_enabled=vault._auth_enabled,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, host: str = "127.0.0.1", port: int = 5000, **kwargs):
        self.flask_app.run(host=host, port=port, **kwargs)
