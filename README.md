# KiCoMa - Kitchen cooking management

## Demo

Check the lastest version at [kicoma.stanislavvalasek.com](https://kicoma.stanislavvalasek.com).

## License

All source code in this repository is released under the **[CC BY‑NC 4.0](https://creativecommons.org/licenses/by‑nc/4.0/)** license.

- ❌ **Commercial use is not permitted**
- 🔒 No patent rights are granted
- 📝 Attribution and copyright notice must be included
- ⚠️ No liability and no warranty

If you'd like to use this software commercially, please [contact me](https://www.stanislavvalasek.com/en/contact/) to discuss a commercial license.

## Data Model

![Data model](./kicoma/static/images/datamodel.png)

## Regularly used commands

### Update static content

`./manage.py collectstatic --noinput`

### Update Translations

#### Generate message files for a desired language

`./manage.py makemessages -l en --ignore=.venv`
`./manage.py makemessages -l cs --ignore=.venv`

#### After adding translations to the .po files, compile the messages

`./manage.py compilemessages --ignore=.venv`

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

If you need to start server manually, the commnad is:
`./manage.py runserver_plus 0.0.0.0:8000`

## Deploy to Hetzner

Commit your changes all relevant files into repo.

```bash
export KAMAL_REGISTRY_PASSWORD=<value>
kamal deploy
```

Connect to server: `ssh root@162.55.185.37`

Free disk space if needed
docker system prune -af --volumes

## Upgrade packages

Run uv lock whenever you change pyproject.toml
uv sync --extra dev        # Install from lockfile

## Update all dependencies to latest compatible versions

Show outdated packages
uv tree --outdated --depth=1
uv lock --upgrade

## Generate lockfile without installing

uv lock
uv add new-package        # Adds to pyproject.toml and updates lockfile
uv remove old-package     # Removes from pyproject.toml and updates lockfile

## Update specific package

uv lock --upgrade-package django

## Update packages in specific group

uv lock --upgrade-package django --upgrade-package gunicorn

### When deploying for the first time, make sure these LOCAL ONLY config files exist

config/django_secret.key
e.g. generate it using <https://djecrety.ir>

config/django_admin_url.key to admin/ or more secure version
config/mailgun_api.key
config/mailgun_public.key
config/mailgun_smtp_login.key
config/mailgun_smtp_password.key

### Update Kamal and kamal proxy on localhost

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

`./manage.py graph_models -a -g -o datamodel.png` or

`./manage.py graph_models kitchen -g -o datamodel.png` and copy the file to statics/images

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

Add dev dependencies into console and run tests

`uv run python manage.py test --settings=config.settings.test`

### Check the production settings

`uv run python manage.py check --deploy --settings=config.settings.production`

## Import data from local machine into it into docker on Hetzner

**Get container ID**:

```bash
scp ./full_dump.json root@162.55.185.37:/root/full_dump.json
ssh root@162.55.185.37
CONTAINER_ID=$(docker ps --format '{{.ID}}' --filter 'name=kicoma-web-' --filter 'ancestor=svalasek/kicoma')
docker cp /root/full_dump.json $CONTAINER_ID:/app/full_dump.json
docker exec -it $CONTAINER_ID python3 manage.py flush --noinput
docker exec -it $CONTAINER_ID python3 manage.py loaddata full_dump.json
```

## Additional info for local development and Cookiecutter info

Check the original repo template:
[Developing locally](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html)

### Settings

[Settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html)

### Live reloading and Sass CSS compilation

[Live reloading and SASS compilation](http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html)
