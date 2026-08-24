#!/bin/bash
set -e

flask db upgrade
exec gunicorn --bind 0.0.0.0:5000 \
	--workers "${WEB_CONCURRENCY:-1}" --threads "${GUNICORN_THREADS:-8}" \
	wsgi:app
