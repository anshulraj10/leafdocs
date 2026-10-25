---
title: Broken Things
tags: [errors]
---

A paragraph before the broken parts. Everything after should still render.

## Invalid mermaid

```mermaid
flowchart LR
    A --> {{{ not valid
    ]]] B
```

A paragraph after the invalid diagram.

## Invalid TeX

This formula is malformed: \(\frac{1}{\) and this one is fine: \(x^2\).

## Unclosed admonition

!!! warning
    This admonition body starts indented
and then the indent stops without a blank line.

A paragraph after the admonition.

## Unclosed code fence

```python
def never_closed():
    return "this fence has no end"
