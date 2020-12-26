# redeploy
# git push heroku master

if [[ $1 == "tri" ]] || [[ $1 == "dobrovec" ]]
then
echo Tenant $1
else
echo Valid tenant required tri/dobrovec but provided: $1
exit
fi

# reset DB
heroku restart --app kicoma-$1
heroku pg:reset DATABASE --confirm kicoma-$1 --app kicoma-$1
heroku run python manage.py makemigrations --app kicoma-$1
heroku run python manage.py migrate --app kicoma-$1

# initialize DB from fixtures
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/druhy-jidla.json
heroku run python manage.py loaddata kicoma/kitchen/fixtures/alergeny.json --app kicoma-$1
heroku run python manage.py loaddata kicoma/kitchen/fixtures/dph.json --app kicoma-$1
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/skupiny-stravniku.json
heroku run python manage.py loaddata kicoma/kitchen/fixtures/skupiny.json --app kicoma-$1
heroku run python manage.py loaddata kicoma/kitchen/fixtures/uzivatele-$1.json --app kicoma-$1
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/article.json
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/recipe.json
# heroku run python manage.py loaddata kicoma/kitchen/fixtures/recipe_article.json

heroku run python manage.py createsuperuser --username admin --app kicoma-$1
