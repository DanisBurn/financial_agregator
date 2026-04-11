"""
Django settings for ProjectZoloto (config package).
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in local setup
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_DIR / '.env')
    load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-n-o(ivdt5+-1w4a5+r9v=-p93eros*)o2o94p&6v9_##lm2&+x')

DEBUG = os.getenv('DJANGO_DEBUG', '1').strip().lower() in {'1', 'true', 'yes', 'on'}

_default_allowed_hosts = ['127.0.0.1', 'localhost', 'testserver']
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', ','.join(_default_allowed_hosts)).split(',')
    if host.strip()
]

MINIAPP_URL = os.getenv('MINIAPP_URL', '').strip()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', os.getenv('BOT_TOKEN', '')).strip()
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', '').strip()
TELEGRAM_AUTH_MAX_AGE = int(os.getenv('TELEGRAM_AUTH_MAX_AGE', '86400'))

if MINIAPP_URL:
    miniapp_parts = urlsplit(MINIAPP_URL)
    miniapp_host = miniapp_parts.hostname
    if miniapp_host and miniapp_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(miniapp_host)
    if miniapp_parts.scheme and miniapp_parts.hostname:
        CSRF_TRUSTED_ORIGINS = [f'{miniapp_parts.scheme}://{miniapp_parts.hostname}']
    else:
        CSRF_TRUSTED_ORIGINS = []
else:
    CSRF_TRUSTED_ORIGINS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rates',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('uz', _('Uzbek')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
