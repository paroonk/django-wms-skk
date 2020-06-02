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
    
Create translation::

    py manage.py makemessages -l th
    py manage.py compilemessages

Runserver::

    py manage.py runserver
