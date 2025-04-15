#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py makemigrations
python manage.py migrate


# Seed DB
# echo "DB: loading groups ..."
# python manage.py loaddata kicoma/kitchen/fixtures/skupiny.json
# echo "DB: loading users ..."
# python manage.py loaddata kicoma/kitchen/fixtures/uzivatele.json
# python manage.py loaddata kicoma/kitchen/fixtures/druhy-jidla.json
# python manage.py loaddata kicoma/kitchen/fixtures/alergeny.json
# python manage.py loaddata kicoma/kitchen/fixtures/dph.json
# python manage.py loaddata kicoma/kitchen/fixtures/skupiny-stravniku.json
# python manage.py loaddata kicoma/kitchen/fixtures/article.json
# python manage.py loaddata kicoma/kitchen/fixtures/recipe.json
# python manage.py loaddata kicoma/kitchen/fixtures/recipe_article.json
# python manage.py loaddata kicoma/kitchen/fixtures/daily_menu.json

# Create super users admim/admin
# echo "Creating super user"
# DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin \
# python manage.py createsuperuser --email=admin@admin.com --noinput

# Running test suite
python manage.py test

# Start server
echo "Starting server"
exec python manage.py runserver_plus 0.0.0.0:8000