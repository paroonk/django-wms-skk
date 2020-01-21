import logging
import multiprocessing

from waitress import serve

from mysite.wsgi import application

logging.getLogger('waitress').setLevel(logging.ERROR)
serve(application, listen="*:8000", threads=multiprocessing.cpu_count())
