#!/bin/bash
set -e

### Generate message files for a desired language
# python ./manage.py makemessages -l cs --ignore=venv/*
# python ./manage.py makemessages -l en --ignore=venv/*

### After adding translations to the .po files, compile the messages
# python manage.py compilemessages

# Collect static files
# python manage.py collectstatic --noinput

# Apply committed migrations before starting the web server.
python manage.py migrate --noinput

# Public demo instance starts from fresh sample data on every deploy.
if [[ "${KICOMA_DEMO_MODE:-}" =~ ^([Tt]rue|1|yes|on)$ ]]; then
	python manage.py reset_demo
fi

# Start Gunicorn (worker count from WEB_CONCURRENCY)
exec gunicorn --bind 0.0.0.0:8000 --preload \
	--access-logfile - --error-logfile - config.wsgi:application
