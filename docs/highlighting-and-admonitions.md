---
title: Highlighting and Admonitions
tags: [guide, code, admonitions]
---

# Highlighting and Admonitions

This page shows syntax highlighted code, every admonition type and the
"On this page" sidebar, which appears on wide screens for docs with three or
more headings.

## Code blocks

Fenced code blocks tagged with a language are highlighted on the server by
Pygments. Untagged fences and unknown languages render as plain code.

### Python

```python
from leafdocs import LeafDocs

ld = LeafDocs(docs_dir="./docs")

@ld.flask_app.route("/health")
def health() -> dict:
    return {"status": "ok"}

if __name__ == "__main__":
    ld.run(debug=True)
```

### Bash

```bash
export LEAFDOCS_PINS="1234,5678"
for f in docs/*.md; do
  echo "found $f"
done
python main.py
```

## Admonitions

Start a block with `!!!`, the type and an optional quoted title, then indent
the body by four spaces.

!!! note
    A note with the default title.

!!! tip "Search tip"
    Tags from frontmatter are matched by the index search box.

!!! info
    Docs are read from disk on every request, so edits show up on reload.

!!! warning "Plain HTTP"
    Set `LEAFDOCS_COOKIE_SECURE=false` when serving over plain HTTP with
    pins, or login will loop.

!!! danger
    Never commit your `.env` file.

!!! success "Done"
    The body can hold lists, code and math:

    - inline code like `ld.run()`
    - inline math like \(a^2 + b^2 = c^2\)

## Summary

Highlighting needs no JavaScript, and the sidebar is pure CSS.
