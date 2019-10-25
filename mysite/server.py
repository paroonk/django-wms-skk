import logging
import multiprocessing

from mysite.wsgi import application
from waitress import serve

logging.getLogger('waitress').setLevel(logging.ERROR)
serve(application, listen="*:8000", threads=multiprocessing.cpu_count())
