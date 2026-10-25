---
title: Long Document
tags: [toc]
---

# Part One

Opening section. Filler text to give the page some height.
A second line of filler.

## Installation

Install the package with pip. Then create a docs directory.

### Requirements

Python 3.10 or newer.

### Virtual Environments

Use a venv to keep dependencies isolated.

#### Creating a venv

Run python -m venv venv in the project root.

#### Activating a venv

Source the activate script for your shell.

## Configuration

Settings come from environment variables.

### Pins

Comma separated list of pins.

### Secret Key

Used to sign session cookies.

### Cookie Security

Set LEAFDOCS_COOKIE_SECURE to false for plain HTTP.

## Fish & Chips <b>bold</b>

This heading has an ampersand and a raw HTML tag in it.

## Writing Docs

Docs are plain Markdown files.

### Frontmatter

Optional title and tags.

### Folders

Nested folders become a tree on the index.

#### Breadcrumbs

The reader shows the folder path above the title.

#### Hidden Folders

Dot folders are skipped.

# Part Two

The second major part of the document.
More filler to extend the page.

## Math

Formulas render with KaTeX.

### Inline

Round bracket delimiters.

### Block

Double dollar or square bracket delimiters.

## Diagrams

Mermaid code fences become diagrams.

### Flowcharts

Boxes and arrows.

### Sequence Diagrams

Actors and messages.

## Security

The sanitizer strips unsafe HTML.

### Allowed Tags

A small allowlist.

### Allowed Attributes

Even smaller.

#### URL Schemes

Only http, https and mailto.

#### Symlinks

Links that escape docs_dir return 403.

# Part Three

Closing part of the document.
Filler line.

## Deployment

Run behind a reverse proxy.

### Gunicorn

Point gunicorn at main:app.

### Systemd

Keep the service running.

## Troubleshooting

Common problems and fixes.

### Login Loop

Usually a Secure cookie over plain HTTP.

### Missing Docs

Check the docs_dir path.

#### Permissions

The server user must be able to read the files.

## Appendix

Final notes.

### Changelog

See CHANGELOG.md.

### License

MIT.

#### Third Party Notices

KaTeX and mermaid are vendored under their own licenses.
