---
title: Manual Test Docs
tags: [test]
---

Content for checking leafdocs by hand. Run a local server from the repo root
with `LEAFDOCS_COOKIE_SECURE=false python main.py` (the flag is needed for
plain http, otherwise login loops when pins are set) and open
`http://127.0.0.1:5000/`. All URLs below are relative to that.

The four symlink cases are not tracked in git. Create them with
`scripts/make-test-symlinks.sh` before testing. The inside, directory and loop
symlinks must all return 404, and the outside symlink must return 403.
`empty-folder/` is not tracked either (git does not store empty directories),
so create it with `mkdir docs/test/empty-folder` to test that case.

This README is itself a doc, so it is listed as "Manual Test Docs".

| File | What it checks | Expected |
| ---- | -------------- | -------- |
| `00-frontmatter-title.md` | Title and list tags from frontmatter | 200, title "Frontmatter Title", tags alpha and beta |
| `01_filename_fallback.md` | Title fallback with no frontmatter | 200, title "01 Filename Fallback" |
| `02-string-tags.md` | Comma separated string tags | 200, tags one, two, three |
| `Zebra-sort-check.md`, `apple-sort-check.md` | Case-insensitive title sort | 200, Apple listed before Zebra |
| `math.md` | Inline `\(...\)`, block `$$` and `\[...\]`, math in lists and tables, `#heading` anchor | 200, KaTeX renders every formula |
| `mermaid.md` | Flowchart, sequence and class diagrams next to math and a python fence | 200, three diagrams render |
| `dollars.md` | Prices and stray `$` signs | 200, every `$` stays plain text |
| `html-and-sanitizer.md` | Script, onerror, javascript and data URLs, iframe, onclick, style, class, details | 200, every payload stripped or neutralized |
| `code-highlighting.md` | Fences in several languages, none, unknown, long line | 200, long line scrolls horizontally |
| `admonitions.md` | `!!!` blocks of each type, unknown type, custom title, rich body | 200, plain text until admonitions are supported |
| `long-doc.md` | 40 headings from h1 to h4, `&` and `<b>` in a heading | 200, every heading gets an id |
| `links-and-images.md` | Relative image and `.md` links, anchor, external link, svg, escaping image path | 200, svg and escaping image return 404 |
| `broken-things.md` | Invalid mermaid, invalid TeX, unclosed admonition and code fence | 200, each error stays inside its block |
| `nested/level-one.md` | Nested doc with frontmatter | 200, breadcrumb Docs / Test / Nested |
| `nested/login.md` | A nested doc named login | 200, listed at `/test/nested/login` |
| `nested/deeper/level-two.md` | Second level breadcrumb | 200, breadcrumb Docs / Test / Nested / Deeper |
| `nested/deeper/deepest/level-three.md` | Relative `../../` links | 200, links reach Level One and Math |
| `nested/deeper/deepest/assets/pixel.png` | Image route | 200, image/png |
| `nested/deeper/deepest/assets/notes.txt` | Non-image, non-markdown file | 404 |
| `nested/deeper/deepest/assets/vector.svg` | SVG is not an allowed image type | 404 |
| `only-assets/pixel.png` | Folder with no docs | Folder not listed, image still 200 |
| `empty-folder/` (untracked) | Empty folder | Not listed, 404 |
| `.hidden/secret.md` | Dot folder | Not listed, `/test/.hidden/secret` returns 404 |
| `symlink-inside.md` (untracked) | Symlink to `math.md` | Not listed, 404 |
| `symlinked-dir` (untracked) | Symlink to `nested/` | Not listed, `/test/symlinked-dir/level-one` returns 404 |
| `loop` (untracked) | Symlink to `..` | Index still loads, `/test/loop/test/math` returns 404 |
| `symlink-outside.md` (untracked) | Symlink to `/tmp/ld-outside.md` | Not listed, 403 |
