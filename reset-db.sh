# Remove a dev DB and initialize from fixtures
rm kicoma.sqlite3
rm -R kicoma/kitchen/migrations/0*.py
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata kicoma/kitchen/fixtures/druhy-jidla.json
python manage.py loaddata kicoma/kitchen/fixtures/alergeny.json
python manage.py loaddata kicoma/kitchen/fixtures/dph.json
python manage.py loaddata kicoma/kitchen/fixtures/skupiny-stravniku.json
python manage.py loaddata kicoma/kitchen/fixtures/skupiny.json
python manage.py loaddata kicoma/kitchen/fixtures/uzivatele.json
python manage.py loaddata kicoma/kitchen/fixtures/article.json
python manage.py loaddata kicoma/kitchen/fixtures/recipe.json
python manage.py loaddata kicoma/kitchen/fixtures/ingredient.json

# https://docs.djangoproject.com/en/3.0/ref/django-admin/#django-admin-createsuperuser
DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_PASSWORD=halahakefa2
DJANGO_SUPERUSER_EMAIL=valasek@gmail.com
echo Creating super user: $DJANGO_SUPERUSER_USERNAME, $DJANGO_SUPERUSER_PASSWORD, $DJANGO_SUPERUSER_EMAIL
python manage.py createsuperuser --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

python manage.py runserver
