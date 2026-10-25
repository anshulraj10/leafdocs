---
title: HTML and Sanitizer
tags: [security]
---

A script tag, which must be removed:

<script>alert(1)</script>

An image with an onerror handler, which must lose the handler:

<img src=x onerror=alert(1)>

A markdown link with a javascript URL, which must lose its href:

[link](javascript:alert(1))

An iframe, which must be removed:

<iframe src="https://example.com"></iframe>

A span with onclick and inline style, which must keep only the text:

<span onclick="x()" style="color:red">span</span>

A div with a disallowed class, which must lose the class:

<div class="evil">div</div>

A link with a data URL, which must lose its href:

<a href="data:text/html,hi">data</a>

A details block, to see what the allowlist does with it:

<details><summary>Details</summary>body</details>

A plain closing sentence after all payloads.
