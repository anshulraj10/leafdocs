# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Security

- Session cookie now sets `Secure` and `SameSite=Lax` in addition to `HttpOnly`. Previously only `HttpOnly` was set.
- Rendered Markdown in the reader view is now sanitized with `nh3` before being inserted into the page. Previously raw HTML in a doc, including `<script>` tags and event handler attributes, was served as-is. The allowlist keeps everything the enabled extensions produce. Raw HTML outside it is stripped.

### Added

- `LEAFDOCS_COOKIE_SECURE` env var, default `true`. Set to `false`, `0`, `no`, or `off` to drop the `Secure` flag when serving over plain HTTP. Deployments that use raw-IP HTTP access with pins must set it to `false`, or login will loop.
- `LEAFDOCS_ALLOW_HTML` env var, default `false`. Set to `true`, `1`, `yes`, or `on` to skip sanitizing. Only safe when you are the sole author of all content.
- `nh3` runtime dependency.

### Fixed

- `docs/authentication.md` claimed the session cookie was `secure` when it was not.

## [0.1.0] - 2026-06-06

### Added

- `LeafDocs` class — wraps a Flask app pointed at a directory of `.md` files
- Auto-discovery of `.md` files on every request, no restart required
- Searchable index at `/` with client-side filtering by title and tags
- Individual document reader at `/<slug>` with Markdown rendered to HTML
- YAML frontmatter support — `title` and `tags` fields, both optional
- Filename fallback for title when frontmatter is absent
- Tags rendered as visual labels on index and reader pages
- Pin-based authentication via `LEAFDOCS_PINS` in `.env`
- Pins hashed with bcrypt at startup, never stored raw
- Session cookie with `httponly` flag
- `LEAFDOCS_SECRET_KEY` env var for stable sessions across restarts
- Path traversal guard on the reader route
- `app.flask_app` exposed for adding custom routes, middleware, and blueprints
- Markdown extensions: fenced code blocks, tables, TOC, newline-to-break
- Dark-themed UI, no external dependencies
- Sample docs and `.env.example` included in the repo
- 24 pytest tests covering open server, auth, path traversal, and constructor behavior
- Deployment guide for AWS EC2 and GCP Compute Engine (Nginx + Gunicorn + systemd)