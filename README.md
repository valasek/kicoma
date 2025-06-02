# KiCoMa - Kitchen cooking management

[![GitHub release](https://img.shields.io/github/release-pre/valasek/kicoma.svg)](https://github.com/valasek/kicoma)
[![GitHub issues](https://img.shields.io/github/issues/valasek/kicoma.svg)](https://github.com/valasek/kicoma/issues)
[![Build Status](https://travis-ci.org/valasek/kicoma.svg?branch=master)](https://travis-ci.org/valasek/kima) [![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg)](https://github.com/pydanny/cookiecutter-django/) [![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

To be fixed:
1/ datum v sekci Nová výdejka z denního menu. Musí se pokaždé ručně zadávat, není možné aby se zobrazilo naposledy použité datum?

2/ je zpřeházené abecední řazení surovin i receptů jak v programu, tak  i na výdejce. Stará verze tento problém neměla.

3/ při tvorbě denního menu při vyhledávání receptů nebo surovin dle počátečního písmena se na poprvé objeví jen jedna náhodná surovina nebo recept začínající na dané písmeno, až při druhém zadání je to správně

4/ v seznamu výdejek bych prosil vrátit starý formát datumu, jde sice jen o zvyk, ale starší verze byla přecejen přehlednější

## Demo

Check the lastest version at [https://kicoma.stanislavvalasek.com](https://kicoma.stanislavvalasek.com).

## License

All source code in the [KiCoMa](https://github.com/valasek/kicoma) is available under the GNU GPL v3 License. See [LICENSE.md](LICENSE.md) for details.

## Getting started

To get started with the app, clone the repo and then install Python 3:

```bash
cd ~/tmp
git clone https://github.com/valasek/kicoma
cd kicoma
```

### Start server locally

Just rebuild the dev container, app is running on port 8000

Alternativelly, install docker and docker compose and run `docker-compose up`

## Deploy to Hetzner

### Make sure these files exist

config/django_secret.key

config/django_admin_url.key

config/mailgun_api.key

config/mailgun_public.key

config/mailgun_smtp_login.key

config/mailgun_smtp_password.key

Commit all relevant files into repo and:

```bash
export KAMAL_REGISTRY_PASSWORD=<value>
kamal deploy
```

Connect to server: `ssh root@162.55.185.37`

### Update Kamal or kamal proxy on localhost

```bash
gem update kamal
kamal proxy upgrade
```

### Path to sqlite

`/var/lib/docker/volumes/kicoma_storage/_data/`

### Sqlite backups to S3

Check if litestream is running:

`sudo journalctl -u litestream -f`

## Usefull Commands

### Run bash inside cosker container

`docker exec -it kicoma-web-1 bash`

### Reset Development DB

`./reset-db.sh`

### Generate user password for fixture

```bash
./manage.py shell
from django.contrib.auth.hashers import make_password
make_password('password')
```

### Generate DB model

Using [Graph models](https://django-extensions.readthedocs.io/en/latest/graph_models.html)

`python3 manage.py graph_models -a -g -o datamodel.png` or

`python3 manage.py graph_models kitchen -g -o datamodel.png` and copy the file to statics/images

### Update Translations

#### Generate message files for a desired language

`./manage.py makemessages -l en -l cs`

#### After adding translations to the .po files, compile the messages

`./manage.py compilemessages`

### Type checks

Running type checks with mypy:

`mypy kicoma`

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report::

```bash
coverage run -m pytest
coverage html
open htmlcov/index.html
```

### Running tests

 ./manage.py test kitchen

### Check the production settings

`./manage.py check --deploy --settings=config.settings.production`

## Data Model

![Data model](./kicoma/static/images/datamodel.png)

## Legacy

### Data migration

#### Export data from Heroku DB

```heroku run "python manage.py dumpdata --exclude auth.permission --exclude contenttypes" --app kicoma-tri > full_dump.json```

Log out all users by deleting all sessions

heroku run python manage.py shell -c --app kicoma-tri "from django.contrib.sessions.models import Session; Session.objects.all().delete()"

#### Import exported data on local machine

```bash
docker-compose exec kicoma_devcontainer-app python manage.py flush --noinput
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py loaddata full_dump.json

or 

docker exec b44a5dc4cfce87e70ab01036acf924d6496bcf974a974998488fdf3bc77ce13b python manage.py flush --noinput
docker exec b44a5dc4cfce87e70ab01036acf924d6496bcf974a974998488fdf3bc77ce13b python manage.py migrate
docker exec b44a5dc4cfce87e70ab01036acf924d6496bcf974a974998488fdf3bc77ce13b python manage.py loaddata full_dump.json
```

#### Import data from local machine into it into docker on Hetzner

**Get container ID**:

```bash
scp ./full_dump.json root@162.55.185.37:/root/full_dump.json
ssh root@162.55.185.37
CONTAINER_ID=$(docker ps --format '{{.ID}}' --filter 'name=kicoma-web-' --filter 'ancestor=svalasek/kicoma')
docker cp /root/full_dump.json $CONTAINER_ID:/app/full_dump.json
docker exec -it $CONTAINER_ID python3 manage.py flush --noinput
docker exec -it $CONTAINER_ID python3 manage.py loaddata full_dump.json
```

### Deploy to Heroku

```bash
heroku login
git push kicoma-tri master
```

[deployment-on-heroku](https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html)

[Managing Multiple Environments for an App](https://devcenter.heroku.com/articles/multiple-environments)

Do not forget to add the following argument at the end of every command:

`--app <app-name>`

`--app kicoma-tri`

#### Set email domain

`heroku config:set MAILGUN_DOMAIN=hospic-cercany.cz`

#### Initialize DB

### Reset Heroku DB

`heroku login`

`./reset-db-heroku.sh`

#### Usefull Heroku commands

```bash
heroku git:remote -a kicoma-tri
heroku apps:info -a kicoma-tri
heroku apps:stacks -a kicoma-tri
heroku buildpacks -a kicoma-tri
heroku config -a kicoma-tri
```

## Additional info for local development and Cookiecutter info

Check the original repo template:
[Developing locally](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html)

### Settings

[Settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html)

### Live reloading and Sass CSS compilation

[Live reloading and SASS compilation](http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html)
