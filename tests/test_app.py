"""
Tests for leafdocs.

Run with:
    pytest tests/ -v
"""

import os
import pathlib
import pytest

from leafdocs import LeafDocs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def docs_dir(tmp_path):
    """A temporary docs directory with sample .md files."""
    # Plain file — no frontmatter
    (tmp_path / "hello.md").write_text("# Hello\n\nThis is a test document.")

    # File with full frontmatter
    (tmp_path / "guide.md").write_text(
        "---\ntitle: The Guide\ntags: [python, tutorial]\n---\n\n# Guide\n\nContent here."
    )

    # File with string tags (not a list)
    (tmp_path / "notes.md").write_text(
        "---\ntitle: My Notes\ntags: research, misc\n---\n\nSome notes."
    )

    return tmp_path


@pytest.fixture
def open_app(docs_dir, monkeypatch):
    monkeypatch.delenv("LEAFDOCS_PINS", raising=False)
    monkeypatch.delenv("LEAFDOCS_SECRET_KEY", raising=False)
    vault = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")
    vault.flask_app.config["TESTING"] = True
    return vault.flask_app.test_client()


@pytest.fixture
def auth_app(docs_dir, monkeypatch):
    """LeafDocs with a single pin set."""
    monkeypatch.setenv("LEAFDOCS_PINS", "correctpin")
    app = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")
    app.flask_app.config["TESTING"] = True
    return app.flask_app.test_client()


# ---------------------------------------------------------------------------
# Open server (no auth)
# ---------------------------------------------------------------------------

class TestOpenServer:
    def test_index_returns_200(self, open_app):
        r = open_app.get("/")
        assert r.status_code == 200

    def test_index_lists_all_docs(self, open_app):
        r = open_app.get("/")
        body = r.data.decode()
        assert "Hello" in body        # filename fallback, titlecased
        assert "The Guide" in body    # from frontmatter title
        assert "My Notes" in body     # from frontmatter title

    def test_index_shows_tags(self, open_app):
        r = open_app.get("/")
        body = r.data.decode()
        assert "python" in body
        assert "tutorial" in body

    def test_reader_renders_markdown(self, open_app):
        r = open_app.get("/hello")
        assert r.status_code == 200
        body = r.data.decode()
        assert "<h1" in body  # TOC extension adds id attr
        assert "test document" in body

    def test_reader_shows_frontmatter_title(self, open_app):
        r = open_app.get("/guide")
        assert r.status_code == 200
        body = r.data.decode()
        assert "The Guide" in body

    def test_reader_shows_tags(self, open_app):
        r = open_app.get("/guide")
        body = r.data.decode()
        assert "python" in body
        assert "tutorial" in body

    def test_reader_string_tags_parsed(self, open_app):
        r = open_app.get("/notes")
        body = r.data.decode()
        assert "research" in body
        assert "misc" in body

    def test_reader_filename_fallback_title(self, open_app):
        r = open_app.get("/hello")
        body = r.data.decode()
        assert "Hello" in body

    def test_404_for_missing_slug(self, open_app):
        r = open_app.get("/does-not-exist")
        assert r.status_code == 404

    def test_login_redirects_to_index_when_no_auth(self, open_app):
        r = open_app.get("/login")
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/")

    def test_logout_redirects_to_login(self, open_app):
        r = open_app.get("/logout")
        assert r.status_code == 302
        assert "login" in r.headers["Location"]


# ---------------------------------------------------------------------------
# Auth-enabled server
# ---------------------------------------------------------------------------

class TestAuthServer:
    def test_index_redirects_to_login_when_unauthenticated(self, auth_app):
        r = auth_app.get("/")
        assert r.status_code == 302
        assert "login" in r.headers["Location"]

    def test_reader_redirects_to_login_when_unauthenticated(self, auth_app):
        r = auth_app.get("/guide")
        assert r.status_code == 302
        assert "login" in r.headers["Location"]

    def test_login_page_renders(self, auth_app):
        r = auth_app.get("/login")
        assert r.status_code == 200
        assert b"pin" in r.data.lower()

    def test_wrong_pin_shows_error(self, auth_app):
        r = auth_app.post("/login", data={"pin": "wrongpin"})
        assert r.status_code == 200
        assert b"Incorrect" in r.data

    def test_correct_pin_redirects_to_index(self, auth_app):
        r = auth_app.post("/login", data={"pin": "correctpin"})
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/")

    def test_authenticated_session_can_access_index(self, auth_app):
        auth_app.post("/login", data={"pin": "correctpin"})
        r = auth_app.get("/")
        assert r.status_code == 200

    def test_authenticated_session_can_access_reader(self, auth_app):
        auth_app.post("/login", data={"pin": "correctpin"})
        r = auth_app.get("/guide")
        assert r.status_code == 200

    def test_logout_clears_session(self, auth_app):
        auth_app.post("/login", data={"pin": "correctpin"})
        auth_app.get("/logout")
        r = auth_app.get("/")
        assert r.status_code == 302
        assert "login" in r.headers["Location"]


# ---------------------------------------------------------------------------
# Session cookie flags
# ---------------------------------------------------------------------------

def _login_set_cookie(docs_dir, monkeypatch, cookie_secure):
    monkeypatch.setenv("LEAFDOCS_PINS", "correctpin")
    if cookie_secure is None:
        monkeypatch.delenv("LEAFDOCS_COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("LEAFDOCS_COOKIE_SECURE", cookie_secure)
    app = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")
    app.flask_app.config["TESTING"] = True
    client = app.flask_app.test_client()
    r = client.post("/login", data={"pin": "correctpin"})
    assert r.status_code == 302
    cookies = [c for c in r.headers.getlist("Set-Cookie") if c.startswith("session=")]
    assert len(cookies) == 1
    return cookies[0]


class TestSessionCookie:
    def test_default_flags(self, docs_dir, monkeypatch):
        cookie = _login_set_cookie(docs_dir, monkeypatch, None)
        assert "HttpOnly" in cookie
        assert "Secure" in cookie
        assert "SameSite=Lax" in cookie

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "FALSE", " Off "])
    def test_secure_disabled(self, docs_dir, monkeypatch, value):
        cookie = _login_set_cookie(docs_dir, monkeypatch, value)
        assert "Secure" not in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie

    @pytest.mark.parametrize("value", ["true", "1", "", "garbage"])
    def test_secure_kept_for_other_values(self, docs_dir, monkeypatch, value):
        cookie = _login_set_cookie(docs_dir, monkeypatch, value)
        assert "Secure" in cookie


# ---------------------------------------------------------------------------
# Rendered Markdown sanitizing
# ---------------------------------------------------------------------------

UNSAFE_DOC = """# Unsafe

<script>alert('xss')</script>

<img src="x.png" onerror="alert(1)">

[click](javascript:alert(1))

<a href="javascript:alert(2)">raw link</a>

<iframe src="https://evil.example.com"></iframe>
"""

FEATURES_DOC = """# Main Title

## Sub Section

[external](https://example.com "Example") and <me@example.com>

![diagram](https://example.com/d.png "Diagram")

| Left | Center | Right |
|:-----|:------:|------:|
| a    | b      | c     |

```python
print("hi")
```
"""


def _reader_client(docs_dir, monkeypatch, allow_html=None):
    (docs_dir / "unsafe.md").write_text(UNSAFE_DOC)
    (docs_dir / "features.md").write_text(FEATURES_DOC)
    monkeypatch.delenv("LEAFDOCS_PINS", raising=False)
    if allow_html is None:
        monkeypatch.delenv("LEAFDOCS_ALLOW_HTML", raising=False)
    else:
        monkeypatch.setenv("LEAFDOCS_ALLOW_HTML", allow_html)
    app = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")
    app.flask_app.config["TESTING"] = True
    return app.flask_app.test_client()


class TestSanitize:
    def test_script_tag_stripped(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/unsafe").data.decode()
        assert "<script>alert" not in body
        assert "alert('xss')" not in body

    def test_onerror_attribute_stripped(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/unsafe").data.decode()
        assert "onerror" not in body
        assert '<img src="x.png">' in body

    def test_javascript_href_stripped(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/unsafe").data.decode()
        assert "javascript:" not in body

    def test_iframe_stripped(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/unsafe").data.decode()
        assert "<iframe" not in body
        assert "evil.example.com" not in body

    def test_heading_ids_survive(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        assert '<h1 id="main-title">Main Title</h1>' in body
        assert '<h2 id="sub-section">Sub Section</h2>' in body

    def test_links_survive_with_rel(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        assert (
            '<a href="https://example.com" title="Example" rel="noopener noreferrer">external</a>'
            in body
        )
        assert 'href="mailto:me@example.com"' in body

    def test_images_survive(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        assert '<img alt="diagram" src="https://example.com/d.png" title="Diagram">' in body

    def test_tables_survive_with_alignment(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        for tag in ("<table>", "<thead>", "<tbody>", "<tr>"):
            assert tag in body
        assert '<th style="text-align:left">Left</th>' in body
        assert '<th style="text-align:center">Center</th>' in body
        assert '<td style="text-align:right">c</td>' in body

    def test_fenced_code_language_class_survives(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        assert '<pre><code class="language-python">' in body

    def test_toc_div_survives(self, docs_dir, monkeypatch):
        (docs_dir / "toc.md").write_text("[TOC]\n\n# One\n\n## Two\n")
        body = _reader_client(docs_dir, monkeypatch).get("/toc").data.decode()
        assert '<div class="toc">' in body
        assert 'href="#one"' in body

    def test_arbitrary_class_and_style_stripped(self, docs_dir, monkeypatch):
        (docs_dir / "attrs.md").write_text(
            '<div class="overlay">x</div>\n\n'
            '| A |\n|:--|\n| <code class="evil">c</code> |\n'
        )
        body = _reader_client(docs_dir, monkeypatch).get("/attrs").data.decode()
        assert "overlay" not in body
        assert 'class="evil"' not in body

    def test_allow_html_passes_script_through(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch, allow_html="true").get("/unsafe").data.decode()
        assert "<script>alert('xss')</script>" in body

    @pytest.mark.parametrize("value", ["false", "0", "", "garbage"])
    def test_allow_html_other_values_still_sanitize(self, docs_dir, monkeypatch, value):
        body = _reader_client(docs_dir, monkeypatch, allow_html=value).get("/unsafe").data.decode()
        assert "<script>alert" not in body


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------

class TestPathTraversal:
    def test_traversal_attempt_returns_404_or_403(self, open_app):
        # URL-encoded traversal — Flask normalizes most of these,
        # but the resolved-path guard catches anything that slips through
        r = open_app.get("/../etc/passwd")
        assert r.status_code in (404, 403, 400)

    def test_slug_with_slashes_rejected(self, open_app):
        r = open_app.get("//etc/passwd")
        assert r.status_code in (404, 403, 400, 308)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_raises_on_missing_docs_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LeafDocs(docs_dir=str(tmp_path / "nonexistent"))

    def test_flask_app_is_accessible(self, docs_dir):
        app = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")
        from flask import Flask
        assert isinstance(app.flask_app, Flask)

    def test_custom_route_on_flask_app(self, docs_dir):
        app = LeafDocs(docs_dir=str(docs_dir), secret_key="test-secret")

        @app.flask_app.route("/health")
        def health():
            return {"status": "ok"}

        client = app.flask_app.test_client()
        r = client.get("/health")
        assert r.status_code == 200
        assert b"ok" in r.data

# ---------------------------------------------------------------------------
# Nested folders
# ---------------------------------------------------------------------------

# 1x1 transparent PNG
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def _write(root, rel, content):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    return path


def _nested_client(root, monkeypatch, pins=None):
    """Client for a LeafDocs app over root. Clears every LEAFDOCS_* env var so a local .env cannot leak in."""
    for var in ("LEAFDOCS_PINS", "LEAFDOCS_SECRET_KEY", "LEAFDOCS_COOKIE_SECURE", "LEAFDOCS_ALLOW_HTML"):
        monkeypatch.delenv(var, raising=False)
    if pins is not None:
        monkeypatch.setenv("LEAFDOCS_PINS", pins)
    app = LeafDocs(docs_dir=str(root), secret_key="test-secret")
    app.flask_app.config["TESTING"] = True
    return app.flask_app.test_client()


class TestNestedDocs:
    def test_nested_doc_listed_and_readable(self, tmp_path, monkeypatch):
        _write(tmp_path, "a/b/c.md", "---\ntitle: Deep Doc\n---\n\nDeep body text.")
        client = _nested_client(tmp_path, monkeypatch)

        body = client.get("/").data.decode()
        assert "Deep Doc" in body
        assert 'href="/a/b/c"' in body

        r = client.get("/a/b/c")
        assert r.status_code == 200
        body = r.data.decode()
        assert "Deep Doc" in body
        assert "Deep body text." in body
        # Breadcrumb: Docs links home, folders are plain text
        assert '<a href="/">Docs</a>' in body
        assert body.index("<span>A</span>") < body.index("<span>B</span>")

    def test_nested_title_and_tag_fallbacks(self, tmp_path, monkeypatch):
        _write(tmp_path, "a/b/my-nested_doc.md", "No frontmatter here.")
        _write(tmp_path, "a/tagged.md", "---\ntags: alpha, beta\n---\n\nTagged.")
        client = _nested_client(tmp_path, monkeypatch)

        body = client.get("/").data.decode()
        assert "My Nested Doc" in body
        assert "Tagged" in body
        assert '<span class="tag">alpha</span>' in body
        assert '<span class="tag">beta</span>' in body

        body = client.get("/a/b/my-nested_doc").data.decode()
        assert "My Nested Doc" in body
        body = client.get("/a/tagged").data.decode()
        assert '<span class="tag">alpha</span>' in body
        assert '<span class="tag">beta</span>' in body

    def test_tree_ordering_folders_first_case_insensitive(self, tmp_path, monkeypatch):
        # Case-sensitive sorting would put "Beta" before "alpha" and "Cherry" before "banana"
        _write(tmp_path, "Beta/one.md", "x")
        _write(tmp_path, "alpha/two.md", "x")
        _write(tmp_path, "c.md", "---\ntitle: Cherry\n---\n")
        _write(tmp_path, "b.md", "---\ntitle: banana\n---\n")
        _write(tmp_path, "a.md", "---\ntitle: Aardvark\n---\n")
        body = _nested_client(tmp_path, monkeypatch).get("/").data.decode()

        order = [
            body.index("<summary>Alpha</summary>"),
            body.index("<summary>Beta</summary>"),
            body.index(">Aardvark</a>"),
            body.index(">banana</a>"),
            body.index(">Cherry</a>"),
        ]
        assert order == sorted(order)

    def test_folders_are_collapsed_by_default(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/setup.md", "x")
        body = _nested_client(tmp_path, monkeypatch).get("/").data.decode()
        assert '<details class="folder">' in body
        assert "<details class=\"folder\" open" not in body

    def test_empty_and_non_md_folders_hidden(self, tmp_path, monkeypatch):
        (tmp_path / "empty" / "deeper").mkdir(parents=True)
        _write(tmp_path, "assets/only.png", PNG_BYTES)
        _write(tmp_path, "assets/notes.txt", "not markdown")
        _write(tmp_path, "real/doc.md", "x")
        body = _nested_client(tmp_path, monkeypatch).get("/").data.decode()
        assert "<summary>Real</summary>" in body
        assert "<summary>Empty</summary>" not in body
        assert "<summary>Deeper</summary>" not in body
        assert "<summary>Assets</summary>" not in body

    def test_hidden_directory_not_listed_and_404(self, tmp_path, monkeypatch):
        _write(tmp_path, ".git/x.md", "---\ntitle: Hidden Secret\n---\n")
        _write(tmp_path, "docs/.draft.md", "---\ntitle: Hidden Draft\n---\n")
        _write(tmp_path, "visible.md", "x")
        client = _nested_client(tmp_path, monkeypatch)

        body = client.get("/").data.decode()
        assert "Hidden Secret" not in body
        assert "Hidden Draft" not in body
        assert "<summary>.Git</summary>" not in body
        assert client.get("/.git/x").status_code == 404
        assert client.get("/docs/.draft").status_code == 404

    def test_symlink_escape_not_listed_and_403(self, tmp_path, monkeypatch):
        outside = _write(tmp_path, "outside/secret.md", "---\ntitle: Outside Secret\n---\n\nTop secret.")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "link.md").symlink_to(outside)
        _write(docs, "visible.md", "x")
        client = _nested_client(docs, monkeypatch)

        body = client.get("/").data.decode()
        assert "Outside Secret" not in body
        r = client.get("/link")
        assert r.status_code == 403
        assert b"Top secret." not in r.data

    def test_symlinked_dir_inside_docs_not_duplicated(self, tmp_path, monkeypatch):
        _write(tmp_path, "a/real/one.md", "---\ntitle: Real One\n---\n")
        _write(tmp_path, "b/two.md", "---\ntitle: Real Two\n---\n")
        (tmp_path / "b" / "linked").symlink_to(tmp_path / "a" / "real", target_is_directory=True)
        body = _nested_client(tmp_path, monkeypatch).get("/").data.decode()

        assert body.count(">Real One</a>") == 1
        assert body.count(">Real Two</a>") == 1
        assert body.count('class="doc-title"') == 2
        assert 'href="/a/real/one"' in body
        assert "/b/linked/" not in body
        assert "<summary>Linked</summary>" not in body

    def test_symlink_loop_does_not_hang(self, tmp_path, monkeypatch):
        import threading

        _write(tmp_path, "one.md", "---\ntitle: Only One\n---\n")
        _write(tmp_path, "sub/two.md", "---\ntitle: Only Two\n---\n")
        (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
        client = _nested_client(tmp_path, monkeypatch)

        # Run in a thread so a regression fails the test instead of hanging the suite
        result = {}
        worker = threading.Thread(target=lambda: result.update(r=client.get("/")), daemon=True)
        worker.start()
        worker.join(timeout=10)
        assert not worker.is_alive(), "index request hung on a symlink loop"

        r = result["r"]
        assert r.status_code == 200
        body = r.data.decode()
        assert body.count(">Only One</a>") == 1
        assert body.count(">Only Two</a>") == 1
        assert body.count('class="doc-title"') == 2
        assert "/loop/" not in body
        assert "<summary>Loop</summary>" not in body

    def test_reserved_top_level_slugs(self, tmp_path, monkeypatch):
        _write(tmp_path, "login.md", "---\ntitle: Top Login\n---\n")
        _write(tmp_path, "logout.md", "---\ntitle: Top Logout\n---\n")
        _write(tmp_path, "guides/login.md", "---\ntitle: Guides Login\n---\n\nNested login doc.")
        client = _nested_client(tmp_path, monkeypatch)

        body = client.get("/").data.decode()
        assert "Top Login" not in body
        assert "Top Logout" not in body
        assert "Guides Login" in body

        r = client.get("/guides/login")
        assert r.status_code == 200
        assert b"Nested login doc." in r.data
        # The built-in route still wins (open server redirects to index)
        r = client.get("/login")
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/")

    def test_static_folder_not_listed(self, tmp_path, monkeypatch):
        _write(tmp_path, "static/x.md", "---\ntitle: Static Doc\n---\n")
        _write(tmp_path, "visible.md", "x")
        body = _nested_client(tmp_path, monkeypatch).get("/").data.decode()
        assert "Static Doc" not in body
        assert "<summary>Static</summary>" not in body

    def test_md_suffix_redirects(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/setup.md", "x")
        r = _nested_client(tmp_path, monkeypatch).get("/guides/setup.md")
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/guides/setup")

    def test_image_served_when_authenticated(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/img/pic.png", PNG_BYTES)
        client = _nested_client(tmp_path, monkeypatch, pins="correctpin")
        client.post("/login", data={"pin": "correctpin"})
        r = client.get("/guides/img/pic.png")
        assert r.status_code == 200
        assert r.mimetype == "image/png"
        assert r.data == PNG_BYTES

    def test_image_redirects_to_login_when_unauthenticated(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/img/pic.png", PNG_BYTES)
        r = _nested_client(tmp_path, monkeypatch, pins="correctpin").get("/guides/img/pic.png")
        assert r.status_code == 302
        assert "login" in r.headers["Location"]

    def test_other_file_types_not_served(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/notes.txt", "plain text")
        _write(tmp_path, "guides/logo.svg", '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        client = _nested_client(tmp_path, monkeypatch)
        assert client.get("/guides/notes.txt").status_code == 404
        assert client.get("/guides/logo.svg").status_code == 404

    def test_image_traversal_rejected(self, tmp_path, monkeypatch):
        _write(tmp_path, "secret.png", PNG_BYTES)
        docs = tmp_path / "docs"
        _write(docs, "guides/img/pic.png", PNG_BYTES)
        r = _nested_client(docs, monkeypatch).get("/guides/../../secret.png")
        assert r.status_code == 404

    def test_auth_enforced_on_nested_docs(self, tmp_path, monkeypatch):
        _write(tmp_path, "a/b/c.md", "Deep body text.")
        client = _nested_client(tmp_path, monkeypatch, pins="correctpin")

        for url in ("/a/b/c", "/a/b/c.md"):
            r = client.get(url)
            assert r.status_code == 302
            assert "login" in r.headers["Location"]

        client.post("/login", data={"pin": "correctpin"})
        r = client.get("/a/b/c")
        assert r.status_code == 200
        assert b"Deep body text." in r.data


# ---------------------------------------------------------------------------
# Math (arithmatex + KaTeX) and diagrams (mermaid)
# ---------------------------------------------------------------------------

KATEX_ASSETS = (
    "/static/vendor/katex/katex.min.css",
    "/static/vendor/katex/katex.min.js",
    "/static/vendor/katex/contrib/auto-render.min.js",
)
MERMAID_ASSET = "/static/vendor/mermaid/mermaid.min.js"
RENDER_ASSET = "/static/reader-render.js"

MATH_DOC = r"""# Math

Inline \(a_b + \alpha\) and \(c_d\).

$$
x_1 \\ y_2
$$

\[
\frac{1}{2}
\]
"""

MERMAID_DOC = """# Diagram

```mermaid
graph TD
  A --> B
```
"""


def _render_client(root, monkeypatch, allow_html=None):
    """Client over root with every LEAFDOCS_* env var cleared, so a local .env cannot leak in."""
    for var in ("LEAFDOCS_PINS", "LEAFDOCS_SECRET_KEY", "LEAFDOCS_COOKIE_SECURE", "LEAFDOCS_ALLOW_HTML"):
        monkeypatch.delenv(var, raising=False)
    if allow_html is not None:
        monkeypatch.setenv("LEAFDOCS_ALLOW_HTML", allow_html)
    app = LeafDocs(docs_dir=str(root), secret_key="test-secret")
    app.flask_app.config["TESTING"] = True
    return app.flask_app.test_client()


class TestMathAndMermaid:
    def test_inline_and_block_math_survive_sanitizing(self, tmp_path, monkeypatch):
        _write(tmp_path, "math.md", MATH_DOC)
        body = _render_client(tmp_path, monkeypatch).get("/math").data.decode()
        assert r'<span class="arithmatex">\(a_b + \alpha\)</span>' in body
        assert r'<span class="arithmatex">\(c_d\)</span>' in body
        assert '<div class="arithmatex">\\[\nx_1 \\\\ y_2\n\\]</div>' in body
        assert '<div class="arithmatex">\\[\n\\frac{1}{2}\n\\]</div>' in body

    def test_less_than_in_math_does_not_break_page(self, tmp_path, monkeypatch):
        _write(tmp_path, "lt.md", "Before \\(x<y\\) middle.\n\nAfter paragraph.\n")
        r = _render_client(tmp_path, monkeypatch).get("/lt")
        assert r.status_code == 200
        body = r.data.decode()
        assert r'<span class="arithmatex">\(x&lt;y\)</span>' in body
        assert "<p>After paragraph.</p>" in body
        assert body.rstrip().endswith("</html>")

    @pytest.mark.parametrize(
        "prose",
        ["Inline $x$ here.", "costs $5 and $10", "$5-$10", "US$5, ($10)"],
    )
    def test_single_dollars_are_not_math(self, tmp_path, monkeypatch, prose):
        _write(tmp_path, "dollars.md", prose + "\n")
        body = _render_client(tmp_path, monkeypatch).get("/dollars").data.decode()
        assert 'class="arithmatex"' not in body
        assert f"<p>{prose}</p>" in body
        assert "/static/vendor/katex/" not in body

    def test_unclosed_double_dollar_is_not_math(self, tmp_path, monkeypatch):
        _write(tmp_path, "dd.md", "The budget went from $$ to more.\n\nNext paragraph.\n")
        body = _render_client(tmp_path, monkeypatch).get("/dd").data.decode()
        assert 'class="arithmatex"' not in body
        assert "<p>The budget went from $$ to more.</p>" in body
        assert "<p>Next paragraph.</p>" in body

    def test_mermaid_fence_emits_language_class(self, tmp_path, monkeypatch):
        _write(tmp_path, "diagram.md", MERMAID_DOC)
        body = _render_client(tmp_path, monkeypatch).get("/diagram").data.decode()
        assert '<pre><code class="language-mermaid">graph TD\n  A --&gt; B\n</code></pre>' in body

    def test_assets_loaded_only_when_needed(self, tmp_path, monkeypatch):
        _write(tmp_path, "math.md", MATH_DOC)
        _write(tmp_path, "diagram.md", MERMAID_DOC)
        _write(tmp_path, "plain.md", "# Plain\n\nNo math, `class=\"arithmatex\"` only as code.\n")
        client = _render_client(tmp_path, monkeypatch)

        body = client.get("/math").data.decode()
        for asset in KATEX_ASSETS + (RENDER_ASSET,):
            assert asset in body
        assert MERMAID_ASSET not in body

        body = client.get("/diagram").data.decode()
        assert MERMAID_ASSET in body
        assert RENDER_ASSET in body
        assert "/static/vendor/katex/" not in body

        body = client.get("/plain").data.decode()
        assert "/static/vendor/" not in body
        assert RENDER_ASSET not in body

        body = client.get("/").data.decode()
        assert "/static/vendor/" not in body
        assert RENDER_ASSET not in body

    def test_render_script_loads_after_vendor_scripts(self, tmp_path, monkeypatch):
        _write(tmp_path, "both.md", MATH_DOC + "\n" + MERMAID_DOC)
        body = _render_client(tmp_path, monkeypatch).get("/both").data.decode()
        render_at = body.index(RENDER_ASSET)
        assert body.index("/static/vendor/katex/contrib/auto-render.min.js") < render_at
        assert body.index(MERMAID_ASSET) < render_at

    def test_payloads_in_math_are_escaped(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "evil.md",
            "\\(<script>alert(1)</script>\\) and \\(<img src=x onerror=alert(2)>\\)\n\n"
            "$$\n</div><script>alert(3)</script>\n$$\n",
        )
        body = _render_client(tmp_path, monkeypatch).get("/evil").data.decode()
        assert "<script>alert" not in body
        assert "<img src=x" not in body
        assert r'<span class="arithmatex">\(&lt;script&gt;alert(1)&lt;/script&gt;\)</span>' in body

    def test_payloads_in_mermaid_are_escaped(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "evil.md",
            '```mermaid\ngraph TD\n  A["<img src=x onerror=alert(1)>"] --> B[<script>alert(2)</script>]\n```\n',
        )
        body = _render_client(tmp_path, monkeypatch).get("/evil").data.decode()
        assert "<script>alert" not in body
        assert "<img src=x" not in body
        assert "&lt;img src=x onerror=alert(1)&gt;" in body

    def test_class_restricted_to_arithmatex_on_span_and_div(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "attrs.md",
            '<span class="arithmatex evil" onclick="x">s</span> <span class="evil">t</span>\n\n'
            '<div class="overlay">d</div>\n',
        )
        body = _render_client(tmp_path, monkeypatch).get("/attrs").data.decode()
        assert "evil" not in body
        assert "overlay" not in body
        assert "onclick" not in body
        assert "<span>s</span>" in body

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ('<span onclick="x()">click</span>', "<span>click</span>"),
            ('<span style="color:red">styled</span>', "<span>styled</span>"),
            ('<span class="arithmatex evil">mixed</span>', "<span>mixed</span>"),
            ('<div class="toc">t</div>', '<div class="toc">t</div>'),
            ('<div class="arithmatex">a</div>', '<div class="arithmatex">a</div>'),
            ('<div class="other">o</div>', "<div>o</div>"),
        ],
    )
    def test_raw_span_and_div_attributes(self, tmp_path, monkeypatch, raw, expected):
        _write(tmp_path, "raw.md", raw + "\n")
        body = _render_client(tmp_path, monkeypatch).get("/raw").data.decode()
        prose = body[body.index('<div class="prose">'):]
        assert expected in prose
        for leftover in ("onclick", "style=", "evil", "other"):
            assert leftover not in prose

    def test_allow_html_still_skips_sanitizing(self, tmp_path, monkeypatch):
        _write(tmp_path, "mixed.md", "\\(a_b\\)\n\n<script>alert('x')</script>\n")
        body = _render_client(tmp_path, monkeypatch, allow_html="true").get("/mixed").data.decode()
        assert r'<span class="arithmatex">\(a_b\)</span>' in body
        assert "<script>alert('x')</script>" in body

    @pytest.mark.parametrize(
        "path, mimetype",
        [
            ("/static/vendor/katex/katex.min.css", "text/css"),
            ("/static/vendor/katex/katex.min.js", "text/javascript"),
            ("/static/vendor/katex/contrib/auto-render.min.js", "text/javascript"),
            ("/static/vendor/katex/fonts/KaTeX_Main-Regular.woff2", "font/woff2"),
            ("/static/vendor/mermaid/mermaid.min.js", "text/javascript"),
            ("/static/reader-render.js", "text/javascript"),
        ],
    )
    def test_vendored_files_served(self, tmp_path, monkeypatch, path, mimetype):
        r = _render_client(tmp_path, monkeypatch).get(path)
        assert r.status_code == 200
        assert r.mimetype == mimetype
        assert len(r.data) > 0
        r.close()

    def test_katex_css_only_references_woff2(self, tmp_path, monkeypatch):
        r = _render_client(tmp_path, monkeypatch).get("/static/vendor/katex/katex.min.css")
        css = r.data.decode()
        r.close()
        assert "url(fonts/" in css
        assert 'format("woff")' not in css
        assert "truetype" not in css
