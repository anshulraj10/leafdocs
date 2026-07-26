---
name: leafdocs
description: Generate Markdown files with correct leafdocs frontmatter (title, tags) ready to drop into a leafdocs docs/ directory. Use this whenever the user asks to create, write, or draft a new leafdocs doc/page/note, wants an existing piece of content turned into a leafdocs-compatible .md file, or mentions "leafdocs", "ld-docs", "uploadld", or their personal docs site. Trigger even if they just paste raw notes and say "make this a doc" or "add this to my docs" — that implies leafdocs formatting, not a generic markdown file.
---

# leafdocs Markdown Generator

Produces a single `.md` file matching the frontmatter schema leafdocs (github.com/anshulraj10/leafdocs) expects, from either raw notes or already-written content.

## Frontmatter schema (authoritative — from the leafdocs README)

```yaml
---
title: My Document Title
tags: [python, tutorial]
---
```

| Field   | Type                            | Fallback if omitted   |
| ------- | -------------------------------- | ---------------------- |
| `title` | string                            | Filename, titlecased    |
| `tags`  | list, or comma-separated string   | None                    |

Both fields are optional per leafdocs itself, but this skill always includes both — a blank/omitted `tags: []` is fine if nothing fits, but never skip the frontmatter block entirely.

## Workflow

1. **Get the content.**
   - If the user pasted raw notes/a brain dump: write it up into a clean, well-structured Markdown document (headings, lists, code blocks as needed), matching the tone the user writes in — don't impose a different voice.
   - If the user already has finished content: use it close to as-is. Light copyediting only — don't restructure content that's already done.

2. **Determine the title.**
   - If the user gave one explicitly, use it verbatim.
   - Otherwise infer a concise, specific title from the content itself (not generic — e.g. "Leafdocs EC2 Deployment Notes", not "Deployment").

3. **Determine the filename.**
   - Slugify the title: lowercase, spaces → hyphens, strip punctuation. E.g. "Leafdocs EC2 Deployment Notes" → `leafdocs-ec2-deployment-notes.md`.
   - If the user gives an explicit filename, use that instead.

4. **Determine tags.**
   - Infer 2–5 relevant tags from the content's actual topics/technologies (lowercase, single words or short hyphenated terms — match the style in the README example: `[python, tutorial]`).
   - If the user explicitly names tags in their request, use exactly those (don't also append inferred ones unless they ask for more).
   - Never invent tags unrelated to the content just to hit a count.

5. **Assemble the file.**
   - YAML frontmatter block first (`title`, then `tags`), then a blank line, then the body content.
   - Tags render as a flow list: `tags: [tag-one, tag-two]`.

6. **Deliver.**
   - Create the actual `.md` file (via `create_file`, not just inline text) and present it for the user to save into their own leafdocs `docs/` directory. Don't attempt to write into any specific docs directory unless the user gives you one explicitly for that request.

## Example output

```markdown
---
title: Leafdocs EC2 Deployment Notes
tags: [leafdocs, aws, deployment]
---

# Leafdocs EC2 Deployment Notes

...body content...
```

## Edge cases

- **No clear topic to tag** (e.g. a short personal note): `tags: []` is fine — don't force unrelated tags.
- **User pastes something that's already a full doc with its own H1/title**: derive `title` from that H1 if no explicit title was given, don't duplicate it as both frontmatter title and first heading text unless that matches their existing convention.
- **Multiple distinct topics in one dump**: ask whether they want one file or split into several, rather than guessing.