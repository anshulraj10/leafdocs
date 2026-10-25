---
title: Admonitions
tags: [admonitions]
---

!!! note
    A note admonition with a single paragraph.

!!! tip
    Use frontmatter tags to make search easier.

!!! info
    The server reads docs from disk on every request.

!!! warning
    Raw HTML is stripped unless LEAFDOCS_ALLOW_HTML is set.

!!! danger
    Never commit your .env file.

!!! success
    The build passed.

!!! banana
    An unknown admonition type.

!!! note "Custom Title Here"
    This note has a custom title.

!!! tip "Rich body"
    A body with richer content:

    - first item with `inline code`
    - second item with math \(a^2 + b^2 = c^2\)
