---
title: Authentication
tags: [security, auth]
---

# Authentication

LeafDocs supports optional pin-based authentication.

## Setup

Add pins to your `.env` file:

```
LEAFDOCS_PINS=mypin123,anotherpin
```

Restart the server. All routes will now require a valid pin.

## How It Works

- Pins are hashed with **bcrypt** at startup — raw values are never stored
- A successful login issues a session cookie with `HttpOnly`, `SameSite=Lax`, and `Secure`
- `Secure` is on by default. Set `LEAFDOCS_COOKIE_SECURE=false` only when serving over plain HTTP, since browsers will not send a `Secure` cookie over HTTP and login will loop
- To invalidate all sessions, rotate or remove the pin and restart

## No Auth

If `LEAFDOCS_PINS` is unset or empty, the server runs open — no login required.
