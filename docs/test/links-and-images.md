---
title: Links and Images
tags: [links]
---

A relative image:

![pixel](nested/deeper/deepest/assets/pixel.png)

A relative markdown link: [level one](nested/level-one.md)

A link with a .md extension and an anchor: [x](math.md#heading)

An absolute external link: [Python docs](https://docs.python.org/3/)

A link to an svg, expected to 404: [vector](nested/deeper/deepest/assets/vector.svg)

An image whose path tries to escape, expected to 404:

![escape](../../../etc/passwd.png)
