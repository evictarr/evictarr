# Installation

## Prerequisites

- Docker and Docker Compose.
- An existing Jellyfin + Seerr (Jellyseerr/Overseerr) + Radarr + Sonarr
  stack already running, all on a shared Docker network. Evictarr joins
  that network - it does not stand up any of those services itself.
- The API key/base URL for each service you want Evictarr to talk to (you
  can leave any of them unconfigured/disabled and add it later).

## Install with Docker (recommended)

Clone the repository and copy the example compose file:

```
git clone https://github.com/evictarr/evictarr.git
cd evictarr/docker
cp docker-compose.yml.example docker-compose.yml
```

There's no separate `.env` file - edit the placeholders directly in
`docker/docker-compose.yml`:

| Placeholder | What it's for |
|---|---|
| `<path_to_your_evictarr_config_folder>` | A host folder for Evictarr's own data (database, auto-generated secrets), bind-mounted to `/config` |
| `<path_to_yours_movies_library>` / `<path_to_yours_shows_library>` | Host paths to your media library, matching what Radarr/Sonarr themselves use. Only needed for the [Orphaned Files](getting-started.md#orphaned-files) report - see below if you don't use that feature. |
| `<your_timezone_ex.Europe/London>` | Your timezone, used for the daily scan schedule |
| `<your_media_network_adapter_name>` | The Docker network your existing stack runs on - find it with `docker network ls`. Set this in the `name:` field under `networks:` at the bottom of the file; leave the `- media-network` line above it as-is, that's just a local alias. |

`SECRET_KEY`/`ENCRYPTION_KEY` need no setup - they're generated on first
run and persisted in `/config` alongside the database. `PUID`/`PGID`
default to `1000`/`1000` - change them in the same file if your host user
differs.

Then build and start it:

```
docker compose up -d --build
```

Evictarr is served on `http://localhost:4378`, with no login required by
default. From here:

1. Go to **Settings > Integrations** and configure Jellyfin, Seerr, Radarr
   and Sonarr (base URL + API key each, with a "test connection" button).
2. Create your first rule under **Rules**.
3. Optionally, go to **Settings > Security** to require a login - see
   [Getting Started](getting-started.md#authentication).

### Skipping the Orphaned Files feature

If you don't want the read-only Orphaned Files report, you can omit the
`/movies`/`/shows` volume mounts entirely (or point them at paths that
don't exist) - the scan just no-ops and everything else works normally.

## Upgrading

There isn't a published container registry image yet - the compose file
builds the image from source, so upgrading means pulling the latest source
and rebuilding:

```
cd evictarr
git pull
cd docker
docker compose up -d --build
```

Database migrations run automatically on every container start (as part of
the entrypoint script, before the app starts serving traffic) - there's no
separate manual migration step. Your data lives entirely in the `/config`
volume and is untouched by an upgrade.

Your `docker/docker-compose.yml` is your own copy (not tracked by git), so
`git pull` never overwrites it. If a future update changes
`docker-compose.yml.example` - a new environment variable, for instance -
diff the two and copy over anything new by hand.

## Uninstalling

```
cd docker
docker compose down
```

This stops and removes the container but leaves your `/config` volume (and
therefore your database, settings, and rules) intact, so you can start it
again later without losing anything. To remove your data as well, also
delete the `config` directory next to `docker-compose.yml` (or run
`docker compose down -v` if you're using a named volume instead of a bind
mount).

## Local development (without Docker)

Backend - uses a local SQLite file (`dev.db`), no external database needed:

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
