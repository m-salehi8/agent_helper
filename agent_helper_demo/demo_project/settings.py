"""Minimal standalone project: agent_helper + the demo plugin on SQLite. Shows that the core works on its own and is
used to check that the wheels install and migrate in a clean virtualenv."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# source checkout: use the sibling packages when they are not installed
for _pkg in ('agent_helper', 'agent_helper_demo'):
    _path = str(BASE_DIR.parent / _pkg)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.append(_path)

SECRET_KEY = 'demo-only-not-secret'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
USE_TZ = False
LANGUAGE_CODE = 'fa'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',
    'django_jalali',
    'agent_helper',
    'agent_helper_demo',
]
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request',
                                       'django.contrib.auth.context_processors.auth',
                                       'django.contrib.messages.context_processors.messages']},
}]
ROOT_URLCONF = 'demo_project.urls'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                         'NAME': os.environ.get('DEMO_DB', str(BASE_DIR / 'demo.sqlite3'))}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication']}

# every endpoint is a URL you configure; nothing points to the internet by default
AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': os.environ.get('ASSISTANT_LLM_BASE_URL', 'http://127.0.0.1:8000/v1'),
}
