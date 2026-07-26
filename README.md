# leafdocs

A lightweight Python library that turns a directory of Markdown files into a self-hosted, searchable web reader.

Install it, point it at a folder, get a running Flask app you can deploy anywhere.

```python
from leafdocs import LeafDocs

ld = LeafDocs(docs_dir="./docs")
ld.run()
```

---

## Installation

```bash
pip install leafdocs
```

---

## Usage

### Minimal setup

```python
from leafdocs import LeafDocs

ld = LeafDocs(docs_dir="./docs")
ld.run()
```

Visit `http://127.0.0.1:5000` — you'll see a searchable index of all `.md` files in your `docs/` directory.

### Constructor arguments

| Argument     | Type            | Default         | Description                                      |
|--------------|-----------------|-----------------|--------------------------------------------------|
| `docs_dir`   | `str`           | `"./docs"`      | Path to the directory containing `.md` files     |
| `secret_key` | `str` or `None` | `None`          | Flask session secret key (see Auth section)      |

### Accessing the Flask app

The underlying Flask app is exposed as `ld.flask_app`. Use it to add routes, middleware, or blueprints:

```python
from leafdocs import LeafDocs

ld = LeafDocs(docs_dir="./docs")

@ld.flask_app.route("/health")
def health():
    return {"status": "ok"}

ld.run()
```

---

## Frontmatter

Each `.md` file can optionally include YAML frontmatter. Supported fields:

```yaml
---
title: My Document Title
tags: [python, tutorial]
---
```

| Field   | Type                           | Fallback             |
|---------|--------------------------------|----------------------|
| `title` | string                         | Filename, titlecased |
| `tags`  | list or comma-separated string | None                 |

Frontmatter is optional — files without it are discovered and served normally.

---

## Authentication

By default the server runs open with no login required.

To enable pin-based auth, add pins to a `.env` file in your working directory:

```
LEAFDOCS_PINS=mypin123,anotherpin
```

Restart the server. All routes will now require a valid pin.

**How it works:**
- Pins are hashed with bcrypt at startup — raw values are never stored in memory
- A successful login issues an `httponly` session cookie
- Multiple pins are supported — useful for sharing access without a shared secret
- To invalidate all sessions, rotate or remove the pin and restart

### Session secret key

By default a random secret key is generated at startup, which means sessions are invalidated on every restart. For persistent sessions across restarts, set a stable key:

```
LEAFDOCS_SECRET_KEY=your-long-random-secret-here
```

Or pass it directly in code:

```python
ld = LeafDocs(docs_dir="./docs", secret_key="your-long-random-secret-here")
```

Generate a good key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Configuration reference

All pins and the secret key are configured via `.env` only. Copy `.env.example` to `.env` to get started:

```
LEAFDOCS_PINS=pin1,pin2
LEAFDOCS_SECRET_KEY=your-secret-here
```

---

## Known limitations

- **No caching** — Markdown is rendered on every request. Fine for personal or low-traffic use; not suitable for high-traffic production serving.
- **No per-device session revocation** — rotating the pin invalidates all active sessions across all devices.
- **No plugin system** — the primary extension hook is `ld.flask_app`. Add routes and middleware directly on the Flask app.

---

## Deployment

> **Disclaimer:** leafdocs is a Flask application. Running it with `ld.run()` uses Flask's built-in development server, which is not suitable for production. For production use, you are responsible for:
> - Running behind a production WSGI server (Gunicorn recommended)
> - Terminating HTTPS at a reverse proxy (Nginx recommended)
> - Managing the process with a supervisor (systemd recommended)

For full production setup on **AWS EC2** or **GCP Compute Engine** — Gunicorn + Nginx + systemd, raw-IP access, and two options for a custom domain (direct DNS + Certbot, or Cloudflare Tunnel for boxes without a public IPv4) — see **[DEPLOY.md](DEPLOY.md)**.

---

## Claude Code skill

[`SKILL.md`](SKILL.md) is a [Claude Code](https://claude.com/claude-code) skill that generates Markdown files with the correct leafdocs frontmatter (`title`, `tags`) from raw notes or existing content, ready to drop into your `docs/` directory. Drop it into your Claude Code skills directory to use it.

---

## Development

```bash
git clone https://github.com/anshulraj10/leafdocs
cd leafdocs
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT