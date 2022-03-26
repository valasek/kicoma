KiCoMa - Kitchen cooking management
==================

[![GitHub release](https://img.shields.io/github/release-pre/valasek/kicoma.svg)](https://github.com/valasek/kicoma)
[![GitHub issues](https://img.shields.io/github/issues/valasek/kicoma.svg)](https://github.com/valasek/kicoma/issues)
[![Build Status](https://travis-ci.org/valasek/kicoma.svg?branch=master)](https://travis-ci.org/valasek/kima) [![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg)](https://github.com/pydanny/cookiecutter-django/) [![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Demo
Check the lastest version at [kicoma-tri.herokuapp.com](https://kicoma-tri.herokuapp.com).

## License

All source code in the [KiCoMa](https://github.com/valasek/kicoma) is available under the GNU GPL v3 License. See [LICENSE.md](LICENSE.md) for details.

## Data Model

![Data model](./kicoma/static/images/datamodel.png)

# Useful Commands

## Reset Development DB
`./reset-db.sh`

## Reset Heroku DB
`./reset-db-heroku.sh`

## Check the production settings
./manage.py check --deploy --settings=config.settings.production

## Generate DB model
Using https://django-extensions.readthedocs.io/en/latest/graph_models.html
* `python3 manage.py graph_models -a -g -o datamodel.png` or
* `python3 manage.py graph_models kitchen -g -o datamodel.png` and copy the file to statics/images

## Update Translations
### Generate message files for a desired language
`./manage.py makemessages -l cs_CZ --ignore=env/*`
 
### After adding translations to the .po files, compile the messages
`./manage.py compilemessages`

# Deploy to Heroku

## Update
`heroku login`

## Update
`git push kicoma-tri master`

## Generate user password for fixture

`./manage.py shell`
`from django.contrib.auth.hashers import make_password`
`make_password('password')`

## External dependencies

* Python
* Django
* Postgresql
* wkhtmltopdf**


## Getting started

To get started with the app, clone the repo and then install Python 3:

```
$ cd ~/tmp
$ git clone https://github.com/valasek/kima
$ cd kima
```
Create python virtual environment, tested is python 3.10.2
`https://towardsdatascience.com/python-environment-101-1d68bda3094d`
`python3 -m venv <virtual env path>`

Switch to the virtual environment:
`source ./env/bin/activate`

Install dependenciec
`pip install -r requirements/local.txt`

migrate the database:

```
$ ./manage.py makemigrations
$ ./manage.py migrate
```

Finally, run the test suite to verify that everything is working correctly:

```
$ ./manage.py test
```

If the test suite passes, you'll be ready to run the app in a local server:

```
$ ./manage.py runserver
```

Getting up and running locally:
https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html

Install WKHTML2PDF:
- `sudo apt-get install wkhtmltopdf`

## Reset DB
`./reset-db.sh`

Settings
--------

Moved to settings_.

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

Basic Commands
--------------

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

* To create an **superuser account**, use this command::

    $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ mypy kicoma

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

Running tests
~~~~~~~~~~~~~~~~~~~~~~~~~~

 ./manage.py test kitchen


::

  $ pytest

Live reloading and Sass CSS compilation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moved to `Live reloading and SASS compilation`_.

.. _`Live reloading and SASS compilation`: http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html


Deployment
----------

The following details how to deploy this application.

Heroku
^^^^^^

## Initial set-up
https://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html

Managing Multiple Environments for an App - https://devcenter.heroku.com/articles/multiple-environments

Do not forget to add the following argument at the end of every command:
` --app <app-name>`
``--app kicoma-tri`
Install WKHTMLtoPDF
`heroku buildpacks:add https://github.com/dscout/wkhtmltopdf-buildpack.git`
More info:
- https://github.com/tutorcruncher/pydf
- https://github.com/dscout/wkhtmltopdf-buildpack
- https://razorjack.net/wkhtmltopdf-on-heroku-evaluating-different-installation-options/

## Set email domain
`heroku config:set MAILGUN_DOMAIN=hospic-cercany.cz`

## Initialize DB
`./reset-db-heroku.sh`
