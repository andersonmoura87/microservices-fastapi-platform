#!/usr/bin/env sh
set -e

# Apply pending migrations before the app starts taking traffic.
alembic upgrade head

exec "$@"
