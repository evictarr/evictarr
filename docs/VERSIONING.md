# Versioning

Evictarr uses `MAJOR.MINOR` version numbers, with a `PATCH` segment appended
only when a patch release is actually needed:

```
0.1   0.2   0.3  ...  1.0   1.1  ...  2.0   2.1   2.2   2.3   2.3.1
```

This is semver-flavored but intentionally looser than strict [SemVer](https://semver.org/)
about the third digit - most releases are just `MAJOR.MINOR`.

## What bumps what

- **MINOR** (`0.1 → 0.2`, `2.2 → 2.3`) - new features, new integrations,
  backward-compatible changes. This is the normal release cadence.
- **PATCH** (`2.3 → 2.3.1`) - bug fixes only, no new features. Only appears
  when a fix can't wait for the next minor. Safe to upgrade without reading
  the changelog closely.
- **MAJOR** (`1.0 → 2.0`) - breaking changes: incompatible config/env var
  changes, breaking API changes, a DB migration that needs manual
  intervention, or removed features.

## The 0.x series

While the app is `0.x`, anything can change release to release - config
format, DB schema, API shape - without a major bump. This is standard
pre-1.0 semver practice. Treat every `0.x → 0.x+1` upgrade as "read the
changelog before upgrading."

## 1.0.0

`1.0.0` marks the first release considered stable and production-ready -
realistically, the public launch. From `1.0` onward, breaking changes get a
MAJOR bump and should come with a migration note in the changelog.

## Source of truth

The version lives in two places, kept in sync by hand at release time:

- `backend/pyproject.toml` → `[project].version`
- `frontend/package.json` → `.version`

There's no build tooling enforcing this yet (single maintainer, low
release frequency) - it's a manual step in the release checklist below.

## Release checklist

1. Move the `[Unreleased]` entries in [`CHANGELOG.md`](../CHANGELOG.md)
   under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
2. Bump the version in `backend/pyproject.toml` and `frontend/package.json`
   to match.
3. Commit: `Release vX.Y.Z`.
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z"` (message can just be the changelog
   section for that version), then `git push && git push --tags`.
5. Pushing the tag triggers `.github/workflows/docker-publish.yml`, which
   builds and pushes `ghcr.io/evictarr/evictarr:X.Y.Z` and `:latest`
   (`linux/amd64` + `linux/arm64`).
6. Once the repo is public: draft a GitHub Release from the tag, pasting in
   the changelog section.

## Pulling the image while the repo is private

GHCR packages inherit the repo's visibility, so right now
`ghcr.io/evictarr/evictarr` is private too - `docker pull`/`compose pull`
needs an authenticated `docker login ghcr.io` (a GitHub PAT with
`read:packages`, or `gh auth token` piped into `docker login`) until either
the repo goes public or the package's visibility is switched to public by
hand under the package's own Settings on GitHub (repo visibility changes
don't always propagate to already-created packages automatically - check
after flipping the repo public).
