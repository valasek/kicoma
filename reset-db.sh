# Remove a dev DB and initialize from fixtures
echo DB: flushing ...
python manage.py flush --noinput
# python manage.py makemigrations
echo DB: migrating ...
python manage.py migrate
# python manage.py loaddata kicoma/kitchen/fixtures/druhy-jidla.json
# python manage.py loaddata kicoma/kitchen/fixtures/alergeny.json
# python manage.py loaddata kicoma/kitchen/fixtures/dph.json
# python manage.py loaddata kicoma/kitchen/fixtures/skupiny-stravniku.json
echo DB: loading groups ...
python3 manage.py loaddata kicoma/kitchen/fixtures/skupiny.json
echo DB: loading users ...
python3 manage.py loaddata kicoma/kitchen/fixtures/uzivatele.json
# python manage.py loaddata kicoma/kitchen/fixtures/article.json
# python manage.py loaddata kicoma/kitchen/fixtures/recipe.json
# python manage.py loaddata kicoma/kitchen/fixtures/recipe_article.json
# python manage.py loaddata kicoma/kitchen/fixtures/daily_menu.json

# https://docs.djangoproject.com/en/3.0/ref/django-admin/#django-admin-createsuperuser
DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=valasek@gmail.com
echo DB: creating super user: $DJANGO_SUPERUSER_USERNAME, password: $DJANGO_SUPERUSER_PASSWORD, email: $DJANGO_SUPERUSER_EMAIL
python manage.py createsuperuser --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

python manage.py runserver
