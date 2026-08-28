# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# gosu drops root privileges after entrypoint.sh remaps the "evictarr" user
# to the requested PUID/PGID - the initial uid/gid here is just a
# placeholder, overwritten at container start.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 evictarr \
    && useradd -u 1000 -g evictarr -M -s /usr/sbin/nologin evictarr

WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/alembic.ini ./
COPY backend/app ./app
RUN pip install .

COPY --from=frontend-build /src/frontend/dist /app/frontend/dist

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PUID=1000 PGID=1000
# Sane defaults for a docker deployment - the DB and auto-generated
# SECRET_KEY/ENCRYPTION_KEY live under /config (the declared volume) instead
# of the container's ephemeral filesystem. Override via `environment:` in
# compose if you need something else (e.g. an external database).
ENV CONFIG_DIR=/config
ENV DATABASE_URL=sqlite+aiosqlite:////config/evictarr.db
RUN mkdir -p /config
VOLUME ["/config"]

EXPOSE 4378
ENTRYPOINT ["/app/entrypoint.sh"]
