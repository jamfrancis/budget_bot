# celery configuration for background task processing
import os
from celery import Celery

# set default django settings module for 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_bot.settings')

app = Celery('budget_bot')

# using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# load task modules from all registered django apps
app.autodiscover_tasks()