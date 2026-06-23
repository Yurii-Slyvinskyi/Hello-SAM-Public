#!/bin/sh
set -e

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  python - <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    parsed_database_url = urlparse(database_url)
    host = parsed_database_url.hostname
    port = parsed_database_url.port or 5432
else:
    host = os.environ.get("POSTGRES_HOST", "db")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))

if not host:
    print("Database host is not configured.", file=sys.stderr)
    sys.exit(1)

deadline = time.time() + 60

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        if time.time() >= deadline:
            print(f"Database is unavailable at {host}:{port}", file=sys.stderr)
            sys.exit(1)
        print(f"Waiting for database at {host}:{port}...")
        time.sleep(1)
PY
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
