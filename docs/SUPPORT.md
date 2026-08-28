# Support

Evictarr is a self-hosted project. All support happens in one place:

**[GitHub Issues](https://github.com/evictarr/evictarr/issues)**

Use it for bug reports, questions, and feature requests alike - there's no
separate email or chat support.

## Before opening an issue

- Check the [Getting Started](getting-started.md) and
  [Installation](installation.md) docs - your question might already be
  answered there.
- Search existing issues to see if someone's already hit the same thing.

## Filing a good bug report

Include:

- What you expected to happen, and what actually happened.
- Steps to reproduce, if you can.
- Relevant logs: `docker compose logs evictarr` (trim to the relevant
  lines - full logs are fine too, just say so).
- How you're running it (Docker Compose vs. local dev) and any recent
  changes to your setup (new integration, changed rule, etc.).

Don't include API keys, session cookies, or other secrets in logs or
screenshots you paste into an issue. If you're reporting a security
vulnerability rather than a bug, see [Security](SECURITY.md) instead - please
don't file those as public issues.
