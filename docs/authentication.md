---
title: Authentication
tags: [security, auth]
---

# Authentication

MDVault supports optional pin-based authentication.

## Setup

Add pins to your `.env` file:

```
MDVAULT_PINS=mypin123,anotherpin
```

Restart the server. All routes will now require a valid pin.

## How It Works

- Pins are hashed with **bcrypt** at startup — raw values are never stored
- A successful login issues a session cookie (`httponly`, `secure`)
- To invalidate all sessions, rotate or remove the pin and restart

## No Auth

If `MDVAULT_PINS` is unset or empty, the server runs open — no login required.
