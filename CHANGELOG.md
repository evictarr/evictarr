# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
See [docs/VERSIONING.md](docs/VERSIONING.md) for how version numbers are
chosen.

## [Unreleased]

## [0.3.0] - 2026-08-29

### Added

- Header now shows a version badge - green when running the latest GitHub
  release, yellow when a newer one is available - linking out to that
  release's GitHub page in a new tab. Backed by a new `GET /api/version`
  route.
- README now has a Screenshots section (Dashboard, Rules, Pending
  Deletions, History) under `docs/images/`.

### Fixed

- Series/season watched cleanup rules ("Series or season watched cleanup")
  never matched, because Jellyfin doesn't stamp `LastPlayedDate` on the
  Season/Series item itself, only on its episodes - the rule read it
  straight off the season/series item and always got nothing, silently
  treating every watched season/series as not yet due. Now derives
  watched-at from the season's (or series') episodes instead. Movie
  cleanup was unaffected.
- Header layout is now responsive - it wraps and stacks instead of
  overflowing the viewport on narrow screens, matching the page content
  below it.

## [0.2.0] - 2026-08-29

### Added

- PR checks workflow (`.github/workflows/pr-checks.yml`) - Super-Linter and
  a CodeQL security scan (Python + JS/TS), run on every pull request
  targeting `main`. Actions are pinned to commit SHA, checkouts set
  `persist-credentials: false`, and a restrictive top-level `permissions:`
  is set per Checkov/`zizmor`'s findings on the workflow itself.
- Docker image published to `ghcr.io/evictarr/evictarr` via GitHub Actions
  on every version tag (`vX.Y[.Z]`), built for `linux/amd64` and
  `linux/arm64`, tagged with both the release version and `latest`.
- `docker/Dockerfile` now has a `HEALTHCHECK` instruction.
- `.markdownlint.json` (allow the same heading text across different
  changelog version sections) and `.trivyignore` (the intentional
  no-`USER` Dockerfile design - PUID/PGID remap needs root at startup,
  see `docker/entrypoint.sh`) added to match this repo's actual
  conventions instead of tools' unconfigured defaults.

### Changed

- `docs/SECURITY.md` now lists a direct email contact alongside GitHub
  Security Advisories.
- `CONFIG_DIR` and `DATABASE_URL` now default to `/config` inside the
  Docker image, so the database and auto-generated secrets persist even if
  a compose file doesn't set them explicitly.
- `docker-compose.yml.example` now pulls the published image instead of
  building from source; building from source is still documented for local
  development.
- Rules page: the "Run this rule now" button now shows a spinning-loader
  animation while the rule is actually running, instead of no visual
  feedback.
- Dashboard: replaced the static placeholder with a real status board -
  approaching-cleanup and exempt (favorited) watched items, plus a
  pending-deletion preview, each with Jellyfin poster art.

### Fixed

- Orphaned-file scan now logs a warning instead of silently scanning
  nothing when `MOVIES_LIBRARY_PATH`/`TV_LIBRARY_PATH` don't resolve to a
  mounted directory.
- PR checks workflow: disabled `VALIDATE_TSX` and `VALIDATE_CSS` in
  Super-Linter - both fought this project's actual conventions (the
  pre-React-17 JSX transform assumption and Node-style import resolution
  the TSX linter expects; the camelCase CSS Modules class names
  `VALIDATE_CSS`'s kebab-case rule rejects) rather than catching real
  issues. First surfaced once a PR actually touched frontend files.

## [0.1.0] - 2026-08-28

Initial feature-complete build. All 7 planned phases done.

### Added

- **Rules engine** - movie-watched, series/season-watched, and stale-request
  cleanup rules, evaluated on a daily schedule or on demand from the Rules
  page.
- **Deletion pipeline** - matches are staged in a Pending Deletions queue
  behind a configurable grace period and can be cancelled before it elapses;
  execution unmonitors in Radarr/Sonarr, removes the Seerr request, and
  deletes the files.
- **Integrations** - Jellyfin, Seerr, Radarr and Sonarr clients, configured
  per-service (base URL + API key) from Settings > Integrations with a
  connection test.
- **Notifications** - optional Discord webhook and/or Telegram bot, sent
  when something is queued, when something is deleted (including partial
  failures), and as a summary after each scheduled scan.
- **History** - a Scans tab (every rule evaluation) and a Deletions tab
  (every deletion attempt with per-system outcome).
- **Orphaned files report** - read-only scan for files on disk that
  Radarr/Sonarr no longer track; never deletes anything itself.
- **Authentication** - off by default; optional Basic auth with
  session-cookie login, TOTP MFA, and self-service password change from
  Settings > Security.
- **CLI recovery commands** - `reset-password`, `disable-mfa`,
  `disable-auth` for emergency access recovery without email-based
  password reset.
- **Docker packaging** - single image serving the API and built frontend
  together, embedded SQLite in a dedicated `/config` volume, PUID/PGID
  support, and auto-generated `SECRET_KEY`/`ENCRYPTION_KEY`.

[Unreleased]: https://github.com/evictarr/evictarr/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/evictarr/evictarr/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/evictarr/evictarr/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/evictarr/evictarr/releases/tag/v0.1.0
