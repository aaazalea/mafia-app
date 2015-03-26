"""
Django settings for mafia project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os


PRODUCTION = ('MAFIA_DJANGO_PRODUCTION' in os.environ)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
if not PRODUCTION:
    SECRET_KEY = '$#2l!+mf(wyu=@vl=@771g!9%4vhg!mqd+^bs2i(^#v&8toe*('
else:
    SECRET_KEY = os.environ['MAFIA_SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True or not PRODUCTION

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['mafia-testing.mit.edu', 'mafia-app.mit.edu', 'jakob.scripts.mit.edu', 'mafia.jakobw.scripts.mit.edu']


# Application definition

INSTALLED_APPS = (
    'django_admin_bootstrapped',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap3',
    'mafia',
    'django_extensions',
)

MIDDLEWARE_CLASSES = (
    'sslify.middleware.SSLifyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'mafia.urls'

WSGI_APPLICATION = 'mafia.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'jakobw+mafia-app',
            'USER': 'jakobw',
            'PASSWORD': os.environ['MAFIA_DB_PASS'],
            'HOST': 'sql.mit.edu',  # Or an IP Address that your DB is hosted on
            'PORT': '3306',
        }
    }
else:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = None

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
    '/var/www/static/',
)

# Mafia

ROGUE_KILL_WAIT = 3
DESPERADO_DAYS = 2
GAY_KNIGHT_INVESTIGATIONS = 2

CONSPIRACY_LIST_SIZE_IS_PERCENT = True
CONSPIRACY_LIST_SIZE = 10

GN_DAYS_LIVE = 2

NO_LYNCH_ALLOWED = True

CLUES_IN_USE = False

MAYOR_COUNT_MAFIA_TIMES = 2
