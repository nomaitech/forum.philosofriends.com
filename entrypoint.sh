#!/bin/sh
set -e

if [ -n "${DATABASE_PATH:-}" ]; then
    mkdir -p "$(dirname "$DATABASE_PATH")"
    if [ ! -f "$DATABASE_PATH" ] && [ -f /app/db.sqlite3 ]; then
        cp /app/db.sqlite3 "$DATABASE_PATH"
    fi
fi

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec "$@"
