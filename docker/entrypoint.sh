#!/bin/sh
set -e

# First pass runs as root: remap the "evictarr" user to the requested
# PUID/PGID, fix up ownership of /config, then re-exec this same script -
# gosu drops privileges for that re-exec, so the second pass (below) runs
# as the target user and does the actual startup work.
if [ "$(id -u)" = "0" ]; then
    PUID=${PUID:-1000}
    PGID=${PGID:-1000}

    if [ "$(id -g evictarr)" != "$PGID" ]; then
        groupmod -o -g "$PGID" evictarr
    fi
    if [ "$(id -u evictarr)" != "$PUID" ]; then
        usermod -o -u "$PUID" evictarr
    fi

    mkdir -p /config
    chown -R evictarr:evictarr /config

    exec gosu evictarr "$0" "$@"
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 4378
