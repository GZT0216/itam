#!/bin/sh
set -eu

echo "[entrypoint] applying database migrations..."
alembic upgrade head

echo "[entrypoint] ensuring initial data..."
python -m app.initial_data

echo "[entrypoint] starting api server..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*'
