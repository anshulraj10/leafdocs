---
title: Getting Started
tags: [guide, setup]
---

# Getting Started

Welcome to **MDVault** — a lightweight Markdown reader you can self-host anywhere.

## Installation

```bash
pip install mdvault
```

## Usage

```python
from mdvault import MDVault

app = MDVault(docs_dir="./docs")
app.run()
```

Point your browser at `http://127.0.0.1:5000` and you'll see this document listed.

## Frontmatter

Each `.md` file can optionally include YAML frontmatter:

```yaml
---
title: My Document Title
tags: [python, tutorial]
---
```

| Field   | Type            | Fallback              |
|---------|-----------------|----------------------|
| `title` | string          | filename (titlecased) |
| `tags`  | list or string  | none                  |

## Extending

Access the underlying Flask app to add your own routes:

```python
app = MDVault(docs_dir="./docs")

@app.flask_app.route("/health")
def health():
    return {"status": "ok"}

app.run()
```
