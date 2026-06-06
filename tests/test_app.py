"""
Tests for mdvault.

Run with:
    pytest tests/ -v
"""

import os
import pathlib
import pytest

from mdvault import MDVault


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
def open_app(docs_dir):
    """MDVault with no auth."""
    vault = MDVault(docs_dir=str(docs_dir), secret_key="test-secret")
    vault.flask_app.config["TESTING"] = True
    return vault.flask_app.test_client()


@pytest.fixture
def auth_app(docs_dir, monkeypatch):
    """MDVault with a single pin set."""
    monkeypatch.setenv("MDVAULT_PINS", "correctpin")
    vault = MDVault(docs_dir=str(docs_dir), secret_key="test-secret")
    vault.flask_app.config["TESTING"] = True
    return vault.flask_app.test_client()


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
            MDVault(docs_dir=str(tmp_path / "nonexistent"))

    def test_flask_app_is_accessible(self, docs_dir):
        vault = MDVault(docs_dir=str(docs_dir), secret_key="test-secret")
        from flask import Flask
        assert isinstance(vault.flask_app, Flask)

    def test_custom_route_on_flask_app(self, docs_dir):
        vault = MDVault(docs_dir=str(docs_dir), secret_key="test-secret")

        @vault.flask_app.route("/health")
        def health():
            return {"status": "ok"}

        client = vault.flask_app.test_client()
        r = client.get("/health")
        assert r.status_code == 200
        assert b"ok" in r.data