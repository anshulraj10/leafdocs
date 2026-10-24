# Vendored front-end libraries

These files are served by the reader from `/static/vendor/...` so math and
diagrams render without a CDN or any runtime network access. Each library's
license is copied next to its files as `LICENSE`.

| Library | Version | License | Source |
|---------|---------|---------|--------|
| KaTeX   | 0.19.0  | MIT     | npm tarball https://registry.npmjs.org/katex/-/katex-0.19.0.tgz |
| mermaid | 12.1.0  | MIT     | npm tarball https://registry.npmjs.org/mermaid/-/mermaid-12.1.0.tgz |

npm `dist.integrity` of the tarballs, checked before extracting:

- katex-0.19.0.tgz: `sha512-v6Tznz3zJ7u3niRCoDTsumM2+HA2XXcCu+WAacCeHD2z3p9A9Ks987o5FzfTGBN0e8A0vjEgIDvLbICrXpdw/Q==`
- mermaid-12.1.0.tgz: `sha512-wlVCp+8eTupfCeeFvoZNNiTuHrvag0P2jz/ILgb/f/6jkVokUefOcujefi8qUe/j2asHiSePncVsz/xzzA80LQ==`

## What was taken from each tarball

KaTeX, from `package/`:

- `dist/katex.min.js` as `katex/katex.min.js`
- `dist/katex.min.css` as `katex/katex.min.css`, modified (see below)
- `dist/contrib/auto-render.min.js` as `katex/contrib/auto-render.min.js`
- `dist/fonts/*.woff2` as `katex/fonts/*.woff2` (woff and ttf not copied)
- `LICENSE` as `katex/LICENSE`

mermaid, from `package/`:

- `dist/mermaid.min.js` as `mermaid/mermaid.min.js` (single-file IIFE build that sets `globalThis.mermaid`)
- `LICENSE` as `mermaid/LICENSE`

## Local modifications

- `katex/katex.min.css`: removed the `woff` and `truetype` fallback
  entries from every `@font-face` `src`, leaving only `woff2`. Font URLs
  stay relative (`url(fonts/...)`), so they resolve to
  `/static/vendor/katex/fonts/` and keep working if the app is mounted
  under a URL prefix.

No other file is modified.

## SHA-256 of vendored files

```
766ccc1f306c885aa45542a9846bbd0a505b27a0374f146778171c2254ce18e3  katex/LICENSE
e5372d199bcdae8b4de71d0f7ceba72a4ba12774a27c60a6f1f77d03b3228ee4  katex/contrib/auto-render.min.js
0cdd387c9590a1a9f9794560022dbb59654a7d86f187aa0c81495ad42d3a7308  katex/fonts/KaTeX_AMS-Regular.woff2
de7701e42cf1f4cf0b766c03fb27977207eee2f4fd5d76fa82188406da43ea4c  katex/fonts/KaTeX_Caligraphic-Bold.woff2
5d53e70ad607c2352162dec9e0923fb54ecdafaccbf604cd8dcf7d00facb989b  katex/fonts/KaTeX_Caligraphic-Regular.woff2
74444efd593c005e3f4573b44524704c0af0a937fe911cca9e94068d0d140d3f  katex/fonts/KaTeX_Fraktur-Bold.woff2
51814d270d06ff0255dba0799994fa4d8c84d11f09951d47595f4abb1f3602dc  katex/fonts/KaTeX_Fraktur-Regular.woff2
0f60d1b897938ec918c8ce073092411baf9438f6739465693ff18b0f9d20b021  katex/fonts/KaTeX_Main-Bold.woff2
99cd42a3c072d918f2f44984a807cf7aa16e13545fd0875fc07c6c65f99e715b  katex/fonts/KaTeX_Main-BoldItalic.woff2
97479ca6cce906abc961ecac96faa5f9ca2e61b8e7670d475826bcdee9a7c267  katex/fonts/KaTeX_Main-Italic.woff2
c2342cd8b869e01752a9321dc17213fc40d4d04c79688c1d43f2cf316abd7866  katex/fonts/KaTeX_Main-Regular.woff2
dc47344dbb6cb5b655c8460d561f4df5f501b90c804ad3c6cec65fe322351ab1  katex/fonts/KaTeX_Math-BoldItalic.woff2
7af58c5ec8f132a2ddde9027c6d7814decce4d3b822a11192a42a20e2e973264  katex/fonts/KaTeX_Math-Italic.woff2
e99ae51144bf1232efcc1bfe5add36262c6866b0faab24fa75740e1b98577a62  katex/fonts/KaTeX_SansSerif-Bold.woff2
00b26ac825e2095056396e0553b8ac26d3f8ad158c3826e28b4c45b385c4714a  katex/fonts/KaTeX_SansSerif-Italic.woff2
68e8c73ef42afd3ccec58bf0fba302cce448938e7fc020a5e31f8a952eee1342  katex/fonts/KaTeX_SansSerif-Regular.woff2
036d4e95149b69ff9bcc0cd55771efeb25ffa3947293e69acd78d5ac328c684b  katex/fonts/KaTeX_Script-Regular.woff2
6b47c40166b6dbe21a5dfca7718413f2147fd2399be1ba605d8ad39cedf25dfe  katex/fonts/KaTeX_Size1-Regular.woff2
d04c54219f9eaec6d4d4fd42dfb28785975a4794d6b2fc71e566b9cd6db842dd  katex/fonts/KaTeX_Size2-Regular.woff2
73d591271b1604960cb10bb90fee021670af7297017e0e98480b332d11f51995  katex/fonts/KaTeX_Size3-Regular.woff2
a4af7d414440a1c1790825cfb700cf9cf43b0f2c4b04f0ebc523011ad9853ec0  katex/fonts/KaTeX_Size4-Regular.woff2
71d517d67827787cfabdf186914cc3358eda539e37931941f2b2fd4a21f68c0b  katex/fonts/KaTeX_Typewriter-Regular.woff2
864f909fc1f3da0f140321d0e277ac0a444d8909e072cdbf174bcea93b95c089  katex/katex.min.css
103a53763cc033bba8d175bf3f0ba597c3505c9b6747dd3f2c7bc2a6bfcc8ae7  katex/katex.min.js
ec9fb67dcb25eccc416ed56e1aab819222c805a2a4bfe4cb19e7556bf2ffde80  mermaid/LICENSE
6484afc32872a3aa16cac9a76ba1816a1ed4cc870a6593cc2e17757750f518b2  mermaid/mermaid.min.js
```
