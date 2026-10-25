"""
Tests for leafdocs.

Run with:
    pytest tests/ -v
"""

import os
import pathlib
import re
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

    def test_fenced_code_is_highlighted(self, docs_dir, monkeypatch):
        body = _reader_client(docs_dir, monkeypatch).get("/features").data.decode()
        assert '<div class="codehilite"><pre><span></span><code><span class="nb">print</span>' in body

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

    def test_symlinked_file_inside_docs_not_listed_and_404(self, tmp_path, monkeypatch):
        _write(tmp_path, "real.md", "---\ntitle: Real Doc\n---\n\nReal body.")
        (tmp_path / "alias.md").symlink_to(tmp_path / "real.md")
        client = _nested_client(tmp_path, monkeypatch)

        body = client.get("/").data.decode()
        assert body.count(">Real Doc</a>") == 1
        assert 'href="/alias"' not in body
        r = client.get("/alias")
        assert r.status_code == 404
        assert b"Real body." not in r.data
        assert client.get("/real").status_code == 200

    def test_doc_through_symlinked_dir_returns_404(self, tmp_path, monkeypatch):
        _write(tmp_path, "a/real/one.md", "Real one body.")
        (tmp_path / "linked").symlink_to(tmp_path / "a" / "real", target_is_directory=True)
        client = _nested_client(tmp_path, monkeypatch)

        r = client.get("/linked/one")
        assert r.status_code == 404
        assert b"Real one body." not in r.data
        assert client.get("/a/real/one").status_code == 200

    def test_doc_through_symlink_loop_returns_404(self, tmp_path, monkeypatch):
        _write(tmp_path, "one.md", "One body.")
        _write(tmp_path, "sub/two.md", "Two body.")
        (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
        client = _nested_client(tmp_path, monkeypatch)

        assert client.get("/").status_code == 200
        for url in ("/loop/one", "/loop/sub/two", "/loop/loop/one"):
            r = client.get(url)
            assert r.status_code == 404, url
        assert client.get("/one").status_code == 200

    def test_symlinked_dir_escape_still_403(self, tmp_path, monkeypatch):
        _write(tmp_path, "outside/secret.md", "Top secret.")
        docs = tmp_path / "docs"
        _write(docs, "visible.md", "x")
        (docs / "out").symlink_to(tmp_path / "outside", target_is_directory=True)
        client = _nested_client(docs, monkeypatch)

        assert "/out/" not in client.get("/").data.decode()
        r = client.get("/out/secret")
        assert r.status_code == 403
        assert b"Top secret." not in r.data

    def test_symlinked_images(self, tmp_path, monkeypatch):
        outside = _write(tmp_path, "outside/secret.png", PNG_BYTES)
        docs = tmp_path / "docs"
        _write(docs, "img/pic.png", PNG_BYTES)
        (docs / "alias.png").symlink_to(docs / "img" / "pic.png")
        (docs / "linked").symlink_to(docs / "img", target_is_directory=True)
        (docs / "loop").symlink_to(docs, target_is_directory=True)
        (docs / "escape.png").symlink_to(outside)
        client = _nested_client(docs, monkeypatch)

        assert client.get("/img/pic.png").status_code == 200
        for url in ("/alias.png", "/linked/pic.png", "/loop/img/pic.png"):
            assert client.get(url).status_code == 404, url
        assert client.get("/escape.png").status_code == 403

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


# ---------------------------------------------------------------------------
# Syntax highlighting, admonitions and the TOC sidebar
# ---------------------------------------------------------------------------

PYGMENTS_CSS = "/static/pygments.css"
MERMAID_HTML = '<pre><code class="language-mermaid">graph TD\n  A --&gt; B\n</code></pre>'
ADMONITION_TYPES = ("note", "tip", "info", "warning", "danger", "success")


def _prose(body):
    """The rendered doc body, without the TOC sidebar."""
    start = body.index('<div class="prose">')
    end = body.find('<aside class="toc-sidebar"', start)
    return body[start:] if end == -1 else body[start:end]


def _sidebar(body):
    start = body.index('<aside class="toc-sidebar"')
    return body[start:body.index("</aside>", start)]


class TestHighlightAdmonitionToc:
    @pytest.mark.parametrize(
        "fence, expected",
        [
            # Spans are checked one by one: whether whitespace gets its own span varies by Pygments version
            (
                "```python\ndef f():\n    return 1\n```",
                ['<span class="k">def</span>', '<span class="nf">f</span>', '<span class="mi">1</span>'],
            ),
            (
                '```bash\necho "$HOME"\n```',
                ['<span class="nb">echo</span>', '<span class="nv">$HOME</span>', '<span class="s2">"</span>'],
            ),
            ('```json\n{"a": 1}\n```', ['<span class="nt">"a"</span>', '<span class="mi">1</span>']),
            # Token subtype outside Pygments' standard list
            ("```yaml\nkey: value\n```", ['<span class="l l-Scalar l-Scalar-Plain">value</span>']),
        ],
    )
    def test_fences_highlighted_and_token_classes_survive(self, tmp_path, monkeypatch, fence, expected):
        _write(tmp_path, "code.md", fence + "\n")
        prose = _prose(_render_client(tmp_path, monkeypatch).get("/code").data.decode())
        assert '<div class="codehilite"><pre><span></span><code>' in prose
        for span in expected:
            assert span in prose

    @pytest.mark.parametrize("opener", ["```", "```nosuchlanguage", "```{ .nosuchlanguage }"])
    def test_unlabeled_and_unknown_fences_render(self, tmp_path, monkeypatch, opener):
        _write(tmp_path, "code.md", f"{opener}\nplain <text> & more\n```\n\nAfter.\n")
        r = _render_client(tmp_path, monkeypatch).get("/code")
        assert r.status_code == 200
        prose = _prose(r.data.decode())
        assert '<div class="codehilite"><pre><span></span><code>plain &lt;text&gt; &amp; more\n</code></pre></div>' in prose
        assert "<p>After.</p>" in prose

    @pytest.mark.parametrize(
        "opener", ["```mermaid", "~~~mermaid", "```.mermaid", "``` mermaid", "```{ .mermaid }", "````mermaid"]
    )
    def test_mermaid_fence_skips_highlighting(self, tmp_path, monkeypatch, opener):
        closer = opener[: len(opener) - len(opener.lstrip("`~"))]
        _write(
            tmp_path,
            "both.md",
            f"{opener}\ngraph TD\n  A --> B\n{closer}\n\n```python\nx = 1\n```\n",
        )
        body = _render_client(tmp_path, monkeypatch).get("/both").data.decode()
        assert MERMAID_HTML in body
        assert MERMAID_ASSET in body
        assert RENDER_ASSET in body
        assert '<span class="n">x</span>' in body

    def test_mermaid_inside_outer_fence_stays_code(self, tmp_path, monkeypatch):
        _write(tmp_path, "nested.md", "````markdown\n```mermaid\ngraph TD\n```\n````\n")
        body = _render_client(tmp_path, monkeypatch).get("/nested").data.decode()
        assert 'class="language-mermaid"' not in body
        assert MERMAID_ASSET not in body
        assert "mermaid" in _prose(body)

    def test_math_next_to_code(self, tmp_path, monkeypatch):
        _write(tmp_path, "mixed.md", "Inline \\(a_b\\).\n\n```python\ns = r\"\\(x\\)\"\n```\n\n$$\ny^2\n$$\n")
        body = _render_client(tmp_path, monkeypatch).get("/mixed").data.decode()
        assert r'<span class="arithmatex">\(a_b\)</span>' in body
        assert '<div class="arithmatex">\\[\ny^2\n\\]</div>' in body
        assert '<div class="codehilite">' in body
        # TeX delimiters inside code stay code, not math
        assert body.count('class="arithmatex"') == 2
        for asset in KATEX_ASSETS + (RENDER_ASSET,):
            assert asset in body

    @pytest.mark.parametrize("kind", ADMONITION_TYPES)
    def test_admonition_types(self, tmp_path, monkeypatch, kind):
        _write(tmp_path, "adm.md", f'!!! {kind} "Heads up"\n    Body text.\n')
        prose = _prose(_render_client(tmp_path, monkeypatch).get("/adm").data.decode())
        assert f'<div class="admonition {kind}">\n<p class="admonition-title">Heads up</p>\n<p>Body text.</p>\n</div>' in prose

    def test_admonition_default_title(self, tmp_path, monkeypatch):
        _write(tmp_path, "adm.md", "!!! warning\n    Body.\n")
        prose = _prose(_render_client(tmp_path, monkeypatch).get("/adm").data.decode())
        assert '<div class="admonition warning">\n<p class="admonition-title">Warning</p>' in prose

    @pytest.mark.parametrize(
        "header, kind",
        [("!!! banana", "note"), ("!!! Banana extra", "note"), ("!!! warning extra", "warning")],
    )
    def test_unknown_admonition_type_falls_back(self, tmp_path, monkeypatch, header, kind):
        _write(tmp_path, "adm.md", f"{header}\n    Body.\n")
        prose = _prose(_render_client(tmp_path, monkeypatch).get("/adm").data.decode())
        assert f'<div class="admonition {kind}">' in prose
        assert re.findall(r'<div class="([^"]*)"', prose) == ["prose", f"admonition {kind}"]
        assert "extra" not in prose

    def test_admonition_rich_body(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "adm.md",
            '!!! tip "Rich"\n    Intro:\n\n    - item with `code`\n    - item with \\(a^2\\)\n',
        )
        body = _render_client(tmp_path, monkeypatch).get("/adm").data.decode()
        prose = _prose(body)
        assert '<div class="admonition tip">' in prose
        assert "<li>item with <code>code</code></li>" in prose
        assert r'<li>item with <span class="arithmatex">\(a^2\)</span></li>' in prose
        assert KATEX_ASSETS[0] in body

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ('<span class="k nf">a</span>', '<span class="k nf">a</span>'),
            ('<span class="k evil-class">a</span>', "<span>a</span>"),
            ('<span class="arithmatex">a</span>', '<span class="arithmatex">a</span>'),
            ('<span class="l l-Scalar">a</span>', '<span class="l l-Scalar">a</span>'),
            ('<span class="k  nf">a</span>', "<span>a</span>"),
            ('<span class="k" onclick="x()" style="color:red">a</span>', '<span class="k">a</span>'),
            ('<div class="admonition note">d</div>', '<div class="admonition note">d</div>'),
            ('<div class="admonition note evil">d</div>', "<div>d</div>"),
            ('<div class="admonition banana">d</div>', "<div>d</div>"),
            ('<div class="codehilite">d</div>', '<div class="codehilite">d</div>'),
            ('<div class="toc" onclick="x()" style="color:red">d</div>', '<div class="toc">d</div>'),
            ('<p class="admonition-title">t</p>', '<p class="admonition-title">t</p>'),
            ('<p class="other">t</p>', "<p>t</p>"),
            ('<p class="admonition-title" onclick="x()" style="color:red">t</p>', '<p class="admonition-title">t</p>'),
            ('<pre class="codehilite">c</pre>', "<pre>c</pre>"),
        ],
    )
    def test_sanitizer_class_rules(self, tmp_path, monkeypatch, raw, expected):
        _write(tmp_path, "raw.md", raw + "\n")
        prose = _prose(_render_client(tmp_path, monkeypatch).get("/raw").data.decode())
        assert expected in prose
        for leftover in ("onclick", "style=", "evil", "banana", "other"):
            assert leftover not in prose

    def test_allow_html_keeps_raw_classes(self, tmp_path, monkeypatch):
        _write(tmp_path, "raw.md", '<p class="other" onclick="x()">t</p>\n\n```python\nx = 1\n```\n')
        body = _render_client(tmp_path, monkeypatch, allow_html="true").get("/raw").data.decode()
        assert '<p class="other" onclick="x()">t</p>' in body
        assert '<span class="n">x</span>' in body

    def test_toc_sidebar_ids_match_headings(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "guide.md",
            "---\ntitle: The Guide\n---\n\n# The Guide\n\n## Alpha\n\n### Beta\n\n## Gamma\n\n## Alpha\n",
        )
        body = _render_client(tmp_path, monkeypatch).get("/guide").data.decode()
        sidebar = _sidebar(body)
        heading_ids = re.findall(r'<h[1-6] id="([^"]+)"', _prose(body))
        link_ids = re.findall(r'href="#([^"]+)"', sidebar)
        # The h1 matching the doc title is left out of the sidebar
        assert heading_ids == ["the-guide", "alpha", "beta", "gamma", "alpha_1"]
        assert link_ids == heading_ids[1:]
        assert '<li class="toc-depth-0"><a href="#alpha">Alpha</a></li>' in sidebar
        assert '<li class="toc-depth-1"><a href="#beta">Beta</a></li>' in sidebar
        assert '<div class="container container-wide">' in body
        assert '<div class="reader-body has-toc">' in body

    def test_h1_not_matching_title_is_listed(self, tmp_path, monkeypatch):
        _write(tmp_path, "doc.md", "---\ntitle: Other\n---\n\n# Intro\n\n## One\n\n## Two\n")
        sidebar = _sidebar(_render_client(tmp_path, monkeypatch).get("/doc").data.decode())
        assert re.findall(r'href="#([^"]+)"', sidebar) == ["intro", "one", "two"]
        assert '<li class="toc-depth-1"><a href="#one">One</a></li>' in sidebar

    @pytest.mark.parametrize(
        "content",
        [
            "# Doc\n\n## One\n\n## Two\n",  # 3 headings, but the h1 matches the title
            "## One\n\n## Two\n",
            "Just text, no headings.\n",
        ],
    )
    def test_no_sidebar_under_three_headings(self, tmp_path, monkeypatch, content):
        _write(tmp_path, "doc.md", content)
        r = _render_client(tmp_path, monkeypatch).get("/doc")
        assert r.status_code == 200
        body = r.data.decode()
        assert "toc-sidebar" not in body.split("</style>")[-1]
        assert '<div class="container">' in body
        assert '<div class="reader-body">' in body

    def test_sidebar_heading_text_escaped(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "evil.md",
            "## Use `<script>` & more\n\n## A <script>alert(1)</script> & B\n\n## Tom &amp; Jerry\n",
        )
        sidebar = _sidebar(_render_client(tmp_path, monkeypatch).get("/evil").data.decode())
        assert '<a href="#use-script-more">Use &lt;script&gt; &amp; more</a>' in sidebar
        assert "<script" not in sidebar
        assert "&amp;amp;" not in sidebar
        assert ">Tom &amp; Jerry</a>" in sidebar

    def test_sidebar_on_nested_doc_keeps_breadcrumb(self, tmp_path, monkeypatch):
        _write(tmp_path, "guides/deep/doc.md", "## One\n\n## Two\n\n## Three\n")
        body = _render_client(tmp_path, monkeypatch).get("/guides/deep/doc").data.decode()
        assert '<span>Guides</span>' in body
        assert '<span>Deep</span>' in body
        assert re.findall(r'href="#([^"]+)"', _sidebar(body)) == ["one", "two", "three"]

    def test_no_state_shared_between_requests(self, tmp_path, monkeypatch):
        _write(tmp_path, "many.md", "## One\n\n## Two\n\n## Three\n")
        _write(tmp_path, "one.md", "## Only\n")
        client = _render_client(tmp_path, monkeypatch)
        assert "toc-sidebar" in client.get("/many").data.decode().split("</style>")[-1]
        body = client.get("/one").data.decode()
        assert "toc-sidebar" not in body.split("</style>")[-1]
        assert '<h2 id="only">Only</h2>' in body
        # A shared toc extension would number a repeated id
        assert '<h2 id="one">One</h2>' in client.get("/many").data.decode()

    def test_pygments_css_served(self, tmp_path, monkeypatch):
        r = _render_client(tmp_path, monkeypatch).get(PYGMENTS_CSS)
        assert r.status_code == 200
        assert r.mimetype == "text/css"
        css = r.data.decode()
        r.close()
        assert ".codehilite .k {" in css
        # Every rule is scoped to .codehilite
        rules = [line for line in css.splitlines() if "{" in line]
        assert rules and all(line.startswith(".codehilite") for line in rules)

    def test_pygments_css_only_on_reader_pages(self, tmp_path, monkeypatch):
        _write(tmp_path, "doc.md", "Plain text.\n")
        client = _render_client(tmp_path, monkeypatch)
        assert PYGMENTS_CSS in client.get("/doc").data.decode()
        assert PYGMENTS_CSS not in client.get("/").data.decode()

        client = _nested_client(tmp_path, monkeypatch, pins="1234")
        r = client.get("/login")
        assert r.status_code == 200
        assert PYGMENTS_CSS not in r.data.decode()
