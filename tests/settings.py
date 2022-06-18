SECRET_KEY = 'not-anymore'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'tests',
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
