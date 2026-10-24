# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.3.0] - 2026-10-25

### Migrating from 0.2.x

- Inline math is `\(...\)` only. A single `$...$` is left as plain text, so docs that use `$x$` for inline math (common in other tools) need converting to `\(x\)`. Block math accepts `$$...$$` and `\[...\]`.
- Raw HTML in docs is now sanitized. Scripts, event handler attributes, iframes, and other tags or attributes outside the allowlist are removed. Set `LEAFDOCS_ALLOW_HTML=true` to keep the old pass-through behavior, only if you are the sole author of all content.
- The session cookie is `Secure` by default, so browsers only send it over HTTPS. If you serve over plain HTTP with pins enabled (for example raw-IP access), set `LEAFDOCS_COOKIE_SECURE=false`, or login will loop back to the login page.

### Security

- Session cookie now sets `Secure` and `SameSite=Lax` in addition to `HttpOnly`. Previously only `HttpOnly` was set.
- Rendered Markdown in the reader view is now sanitized with `nh3` before being inserted into the page. Previously raw HTML in a doc, including `<script>` tags and event handler attributes, was served as-is. The allowlist keeps everything the enabled extensions produce. Raw HTML outside it is stripped.

### Added

- `LEAFDOCS_COOKIE_SECURE` env var, default `true`. Set to `false`, `0`, `no`, or `off` to drop the `Secure` flag when serving over plain HTTP. Deployments that use raw-IP HTTP access with pins must set it to `false`, or login will loop.
- `LEAFDOCS_ALLOW_HTML` env var, default `false`. Set to `true`, `1`, `yes`, or `on` to skip sanitizing. Only safe when you are the sole author of all content.
- `nh3` runtime dependency.
- Nested folders. Docs are discovered recursively under `docs_dir`, and the index shows them as a collapsible folder tree. Folders with no docs beneath them are omitted.
- Search on the index also matches the doc path, and opens the folders that hold matches.
- Image route. `.png`, `.jpg`, `.jpeg`, `.gif`, and `.webp` files inside `docs_dir` are served at their path, behind the same auth check and path guard as docs.
- Sample nested docs under `docs/guides/`.
- Math rendering. `pymdownx.arithmatex` (generic mode) marks up inline `\(...\)` and block `$$...$$` and `\[...\]`, and a bundled copy of KaTeX 0.19.0 renders it in the browser. Inline math is `\(...\)` only: single `$...$` is not treated as math, so prices such as `$5-$10` in prose render as written.
- Mermaid diagrams. Fenced code blocks tagged `mermaid` are rendered in the browser by a bundled copy of mermaid 12.1.0, with `securityLevel: "strict"` and a theme taken from the dark palette.
- KaTeX and mermaid load only on pages that contain math or diagrams. Both are served from `/static/vendor/`, with no CDN or runtime network access. Versions, sources, and checksums are in `src/leafdocs/static/vendor/VERSIONS.md`, with each license next to its files.
- `pymdown-extensions` runtime dependency.
- Sample doc `docs/math-and-diagrams.md`.
- Root `main.py` for local development. `python main.py` runs a dev server on `http://127.0.0.1:5000` with the `Secure` cookie flag off for plain HTTP. It is not included in the wheel or sdist.

### Changed

- The reader route is now `/<path:slug>`, where the slug is the path relative to `docs_dir` without `.md`. Top-level docs keep their existing URLs.
- URLs ending in `.md` redirect to the same URL without it.
- Discovery and the reader skip hidden paths (any part starting with `.`), symlinks that resolve outside `docs_dir`, and the reserved top-level slugs `login`, `logout`, and `static/...`.
- The reader's back link is replaced with a breadcrumb of the doc's folders.
- The sanitizer allowlist now keeps `span` elements and allows `class="arithmatex"` on `span` and `div`. Any other `class` value on those tags is still removed.

### Fixed

- `docs/authentication.md` claimed the session cookie was `secure` when it was not.

## [0.2.0] - 2026-07-26

### Added

- `DEPLOY.md`, a production deployment guide for AWS EC2 and GCP Compute Engine (Gunicorn, Nginx, systemd), covering raw-IP access and two custom domain options (direct DNS with Certbot, or Cloudflare Tunnel).
- `SKILL.md`, a Claude Code skill that generates Markdown files with leafdocs frontmatter (`title`, `tags`).

### Changed

- README deployment section trimmed to a short summary that links to `DEPLOY.md`.

### Fixed

- `.DS_Store` files are now ignored by git.

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