from .settings import *  # noqa: F403


INSTALLED_APPS.extend(['django.contrib.postgres', 'atris', 'tests'])  # noqa: F405

MIDDLEWARE.extend(['atris.middleware.LoggingRequestMiddleware'])  # noqa: F405

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'history_db',
        'USER': 'history_user',
        'PASSWORD': 'pass',
        'HOST': 'db',
        'TEST': {'NAME': 'test_history_db'},
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TIME_ZONE = 'UTC'

USE_TZ = True
