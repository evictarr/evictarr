# Evictarr

Media stack cleanup companion for Jellyfin, Seerr, Radarr and Sonarr. It
scans your library for watched movies/seasons and stale requests, stages
matches for deletion behind a cancellable grace period, then actually
deletes them (Seerr request removed, Radarr/Sonarr unmonitored, files
removed) once the grace period elapses.

📖 **[Full documentation](docs/)** - [Getting Started](docs/getting-started.md)
(architecture, how it works, every feature explained) ·
[Installation](docs/installation.md) · [Support](docs/SUPPORT.md) ·
[Security](docs/SECURITY.md) · [Changelog](CHANGELOG.md) ·
[Versioning](docs/VERSIONING.md)

## Status

All 7 phases are complete:

- **Auth**: off by default (no login wall, matching first-run Sonarr/Radarr
  behavior) - optionally enable Basic (session-cookie login) from Settings >
  Security, with optional TOTP MFA and self-service password change on top.
- **Integrations**: Jellyfin, Seerr, Radarr and Sonarr clients with a
  Settings page to configure base URL/API key per service and test the
  connection.
- **Rules engine**: movie watched cleanup, series/season watched cleanup and
  stale request cleanup, evaluated on a daily schedule or on demand from the
  Rules page. Every match and notable skip is logged to the History page.
- **Deletion pipeline**: matches are staged in a Pending Deletions queue and
  only actually deleted once the configurable grace period elapses - cancel
  anything from the Pending page before then. Grace period, daily scan time
  and check interval are configurable from Settings > General.
- **Notifications**: optional Discord webhook and/or Telegram bot, notified
  when something is queued, when something is actually deleted (including
  partial failures), and with a summary after each scheduled scan.
- **History**: a Scans tab (every rule evaluation) and a Deletions tab
  (every actual deletion attempt with per-system outcome) - answers "what
  was deleted, and when".
- **Orphaned files**: a read-only report of files on disk Radarr/Sonarr no
  longer track. Runs after each scheduled scan or on demand; never deletes
  anything itself, just flags it for you to clear once reviewed.
- **Docker packaging**: single image serving the API and the built frontend
  together, with an embedded SQLite database stored in its own /config
  volume, PUID/PGID support, and auto-generated secrets - joining your
  existing media stack's docker network to reach Jellyfin/Seerr/Radarr/
  Sonarr.

## Running with Docker (recommended)

Evictarr joins the docker network your Jellyfin/Seerr/Radarr/Sonarr stack
already runs on - it does not stand up those services itself.

```
cd docker
cp docker-compose.yml.example docker-compose.yml
```

Edit `docker/docker-compose.yml` directly - no separate `.env` file, just
fill in the placeholders in place:
- `<path_to_your_evictarr_config_folder>` - a host folder for Evictarr's
  own data (database, auto-generated secrets)
- `<path_to_yours_movies_library>` / `<path_to_yours_shows_library>` - host
  paths to your media library, matching what Radarr/Sonarr themselves use
  (mounted read-only, used only by the orphaned-file scan)
- `<your_timezone_ex.Europe/London>` - your timezone, used for the daily
  scan schedule
- `<your_media_network_adapter_name>` (appears twice - the `networks:` name
  at the bottom only) - the docker network your existing stack runs on
  (`docker network ls` to find it)

`SECRET_KEY`/`ENCRYPTION_KEY` need no setup - they're generated on first run
and persisted in `/config` alongside the database. `PUID`/`PGID` default to
1000/1000 - change them in the same file if your host user differs.

Then:

```
docker compose up -d
```

This pulls the published image from `ghcr.io/evictarr/evictarr`. To build
from source instead (e.g. for local changes), replace the `image:` line
with:

```yaml
build:
  context: ..
  dockerfile: docker/Dockerfile
```

Evictarr is served on `http://localhost:4378` with no login required.
Configure Jellyfin/Seerr/Radarr/Sonarr under Settings > Integrations before
creating any rules. To require a login, go to Settings > Security and turn
on Basic authentication.

## Local development (without Docker)

Backend - uses a local SQLite file (dev.db), no external database needed:

```
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
```

Create `backend/.env`:

```
DATABASE_URL=sqlite+aiosqlite:///dev.db
SESSION_COOKIE_SECURE=false
```

`SECRET_KEY`/`ENCRYPTION_KEY` aren't needed here either - they're
auto-generated on first run and persisted as `backend/.secret_key` /
`backend/.encryption_key` (gitignored).

```
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Frontend (proxies `/api` to `http://127.0.0.1:8000` in dev, see
`vite.config.ts`):

```
cd frontend
npm install
npm run dev
```

## Emergency access recovery

Evictarr has no email-based password recovery by design. If you're locked
out:

```
docker compose exec evictarr python -m app.cli reset-password --username admin --new-password ...
docker compose exec evictarr python -m app.cli disable-mfa --username admin
docker compose exec evictarr python -m app.cli disable-auth
```

`reset-password` overwrites the password directly (no need to know the old
one) and works even if no user exists yet. `disable-auth` is a further
fallback that turns the login requirement off entirely (back to "None"),
without touching the stored credentials - useful if you'd rather just open
the app back up than reset a password.
