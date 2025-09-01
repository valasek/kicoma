# redeploy
# git push heroku master

# reset DB
heroku restart --app kicoma-tri
heroku pg:reset DATABASE --confirm kicoma-tri --app kicoma-tri
heroku run python manage.py makemigrations --app kicoma-tri
heroku run python manage.py migrate --app kicoma-tri

# initialize DB from fixtures
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/druhy-jidla.json
heroku run python manage.py loaddata kicoma/kitchen/fixtures/alergeny.json --app kicoma-tri
heroku run python manage.py loaddata kicoma/kitchen/fixtures/dph.json --app kicoma-tri
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/skupiny-stravniku.json
heroku run python manage.py loaddata kicoma/kitchen/fixtures/skupiny.json --app kicoma-tri
heroku run python manage.py loaddata kicoma/kitchen/fixtures/uzivatele.json --app kicoma-tri
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/article.json
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/recipe.json
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/recipe_article.json

heroku run python manage.py createsuperuser --username admin --app kicoma-tri
