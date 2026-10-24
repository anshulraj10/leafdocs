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