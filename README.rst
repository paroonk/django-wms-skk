Django-WMS-SKK
--------------
WMS Program for Paperbag Plant SKK

Create django project::

    django-admin startproject mysite
    py manage.py startapp wms

When changing model::

    py manage.py makemigrations wms
    py manage.py migrate

Create admin::

    py manage.py createsuperuser

Serve static:

    in settings.py set STATIC_ROOT = 'static' and run::

        py manage.py collectstatic

    which will copy the Django admin static files to /path/to/project/static/

Runserver::

    py manage.py runserver

Python Anywhere::

    use paroonk$mysite;
    source mysite.sql;

Virtualenv::

    mkvirtualenv venv --python=/usr/bin/python3.7
    which python
    deactivate
    workon venv

