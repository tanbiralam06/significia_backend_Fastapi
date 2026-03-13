#!/bin/sh

set -e

echo "Starting Significia service..."

if [ "$1" = "api" ]; then
    echo "Running FastAPI server"
    if [ "$RELOAD" = "true" ]; then
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    else
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    fi
fi

if [ "$1" = "worker" ]; then
    echo "Starting Celery worker"
    exec celery -A app.tasks.celery_app worker \
        --loglevel=info
fi

exec "$@"