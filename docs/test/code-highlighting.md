---
title: Code Highlighting
tags: [code]
---

Inline code looks like `pip install leafdocs` or `LEAFDOCS_PINS=1234`.

## Python

```python
from leafdocs import LeafDocs

ld = LeafDocs(docs_dir="./docs")
if __name__ == "__main__":
    ld.run(debug=True)
```

## Bash

```bash
export LEAFDOCS_COOKIE_SECURE=false
python main.py && curl -s http://127.0.0.1:5000/ | head
```

## JSON

```json
{"title": "Getting Started", "tags": ["setup", "intro"], "draft": false}
```

## YAML

```yaml
title: Getting Started
tags:
  - setup
  - intro
```

## SQL

```sql
SELECT slug, title FROM docs WHERE tags LIKE '%setup%' ORDER BY title;
```

## JavaScript

```js
document.querySelectorAll('.doc-item').forEach(el => console.log(el.dataset.slug));
```

## Diff

```diff
- _MARKDOWN_EXTENSIONS = ["fenced_code", "tables"]
+ _MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "toc"]
```

## No language

```
plain text block
with two lines
```

## Unknown language

```nonsense
this language does not exist ::: <> {}
```

## Long line

```python
result = some_function_with_a_long_name(argument_one="value one", argument_two="value two", argument_three="value three", argument_four="value four", argument_five="value five")
```
