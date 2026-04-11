#!/bin/sh
set -eu

mkdir -p /data

python /app/web/manage.py migrate --noinput

exec gunicorn \
  --chdir /app/web \
  config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WEB_CONCURRENCY:-2} \
  --timeout ${GUNICORN_TIMEOUT:-120}
