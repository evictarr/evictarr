# Dashboard design

Status: approved, pending implementation plan.

## Problem

`frontend/src/pages/Dashboard.tsx` is a static placeholder - it makes no
API calls and always shows "Nothing to show yet," regardless of real
state. This design replaces it with a curated status board: what's
watched and approaching cleanup, what's watched but exempt, and a preview
of what's already staged for deletion - each with poster art, not just
titles.

Explicitly out of scope: a full browsable library (every movie/show,
watched or not) - the app doesn't need a second, worse Jellyfin. Also out
of scope: `stale_request_cleanup` rules (unfulfilled Seerr requests aren't
"watched media").

## Data sources

Three independent fetches from the Dashboard page, each degrading
gracefully on its own:

1. **Pending deletions** (existing, unchanged) - `GET
   /api/pending-deletions?status=pending`, capped client-side to the
   soonest ~6 by `execute_after`, with a "View all →" link to the
   existing Pending Deletions page.
2. **Approaching / exempt watched items** (new) - `GET
   /api/dashboard/watched-status`. Live, on-demand computation (no new
   persisted state) over the currently *enabled*
   `movie_watched_cleanup`/`series_watched_cleanup` rules only.
   - "Approaching": watched, not yet past the rule's threshold.
   - "Exempt": watched, past threshold, but favorited (so the real scan
     would skip staging it).
   - Items past threshold and *not* exempt aren't included here - a real
     scan stages those as pending deletions in the same instant, so
     they're already covered by source 1.
3. **Posters** (new) - `GET /api/media/poster/{jellyfin_item_id}`, a
   backend proxy to Jellyfin's `/Items/{id}/Images/Primary`, using the
   already-stored/decrypted Jellyfin API key. The browser never talks to
   Jellyfin directly. All three sections resolve their poster through
   this one endpoint via the `jellyfin_item_id` already present in
   `external_ids` (pending deletions) or read directly off the Jellyfin
   item (watched-status).

## Backend changes

### `rules/base.py`

`RuleResult` gains an optional `items: list[dict]` field, populated only
in dry-run mode (empty list otherwise). Each item dict: `title`,
`media_type`, `jellyfin_item_id`, `watched_at` (ISO), `rule_id`,
`rule_name`, `status` (`"approaching"` or `"exempt"`), and for
`"approaching"` items, however much of the threshold window remains
(reuse `thresholds.py` math, add a small helper alongside
`is_past_threshold` rather than recomputing it ad hoc).

### `rules/movie_watched.py`, `rules/series_watched.py`

`evaluate()` gains `dry_run: bool = False`. Existing behavior is the
`dry_run=False` path, unchanged. When `dry_run=True`:

- Items not yet past threshold, which today are silently `continue`d,
  get appended to `result.items` with `status="approaching"` instead of
  being discarded.
- Items past threshold and favorited get appended with
  `status="exempt"` instead of calling `log_event()`.
- `stage()` and `log_event()` are never called - dry-run makes no DB
  writes beyond the `RuleResult` returned to the caller.
- All existing matching/lookup logic (Jellyfin/Radarr/Sonarr/Seerr calls,
  TMDB/TVDB id resolution, favorite checks) is reused as-is; only the
  three branch endings (approaching / exempt / matched) change behavior
  based on the flag.

`rules/stale_request.py` is not touched.

### `rules/engine.py`

New `preview_watched_status(db) -> dict` alongside `run_scan()`: queries
enabled rules where `rule_type` is `movie_watched_cleanup` or
`series_watched_cleanup`, calls `evaluate(db, run_id=None, rule, ctx,
dry_run=True)` for each via the same `_HANDLERS` dispatch, and merges
each rule's `result.items` into two lists (`approaching`, `exempt`) split
by `status`. An `IntegrationError` from one rule's evaluation is caught
and that rule is skipped (mirrors `run_scan`'s existing per-rule error
handling) rather than failing the whole preview.

`evaluate()`'s `run_id: int` parameter is typed non-optional today
(it's always a real `Run.id` on the real-scan path). For the dry-run
path, widen it to `run_id: int | None = None` - `preview_watched_status`
calls `evaluate(db, None, rule, ctx, dry_run=True)`, and since
`log_event()` (the only thing that reads `run_id`) is never called when
`dry_run=True`, passing `None` is safe.

### New route: `GET /api/dashboard/watched-status`

Calls `preview_watched_status(db)`, returns `{"approaching": [...],
"exempt": [...]}`. No new DB table, no migration.

### New route: `GET /api/media/poster/{jellyfin_item_id}`

Loads the Jellyfin integration, decrypts its API key, streams
`{base_url}/Items/{jellyfin_item_id}/Images/Primary` back with a
`Cache-Control` header (poster art rarely changes - a long-ish max-age is
fine). Returns 404 if Jellyfin isn't configured, the item has no image,
or the upstream call fails - the frontend treats any non-200 as "show the
placeholder," not an error state.

## Frontend changes

### `Dashboard.tsx` (replaces the current stub)

On mount, fires both fetches (pending-deletions, watched-status)
independently - one failing/being empty doesn't block the other from
rendering. Renders three sections, each with its own heading, grid of
`PosterCard`s, and empty state:

- **Approaching cleanup** - poster, title, rule name, remaining-time text
  (e.g. "watched 25 of 30 days ago").
- **Exempt (favorited)** - poster, title, "favorited - kept regardless."
- **Pending deletion** - poster, title, countdown in the same "in 20h
  58m" format the Pending Deletions page already uses; capped to 6 items
  with a "View all →" link to that page.

Page-level loading state while both fetches are in flight (reuses the
spinner styling added for the Rules page's "Run now" button). Per-section
empty states, not one blanket placeholder - a partially-configured setup
still shows what's available.

### New `PosterCard` component

Shared across all three sections: poster `<img>` pointing at
`/api/media/poster/{id}`, title, and a slot for the section-specific
status line. `onError` on the image swaps to a plain placeholder box
(no broken-image icon).

## Error handling summary

| Failure | Behavior |
|---|---|
| Jellyfin not configured / unreachable | `watched-status` returns empty lists; poster proxy 404s per-item → placeholders |
| One rule's evaluation throws `IntegrationError` | That rule is skipped, others still contribute to the preview |
| Pending-deletions fetch fails | That section shows its own error/empty state; other two sections unaffected |
| Individual poster fails to load | `PosterCard` falls back to a placeholder box, doesn't break the grid |

## Testing

The backend has `pytest`/`pytest-asyncio` as dev dependencies but no
existing test files (`backend/` has no `test_*.py` today) - this would
be the first. New tests for: `dry_run=True` producing `"approaching"` and
`"exempt"` items correctly (mocked Jellyfin/Radarr/Sonarr/Seerr clients),
and confirming `dry_run=True` never calls `stage()`/`log_event()`. Poster
proxy: happy path, and Jellyfin-not-configured/unreachable → 404.

The frontend has no test runner configured (`package.json` has no
vitest/jest) - adding one is out of scope for this feature unless
explicitly requested separately. Frontend verification is manual/visual
(covered by the `run` skill or manual testing against a real or
mocked-integration setup), consistent with how the rest of the frontend
is currently verified.
