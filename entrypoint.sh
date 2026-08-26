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

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --preload \
	--access-logfile - --error-logfile - config.wsgi:application
