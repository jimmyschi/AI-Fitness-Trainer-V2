import os
from pathlib import Path
from dotenv import load_dotenv
from storages.backends.gcloud import GoogleCloudStorage
from google.oauth2 import service_account
from google.cloud import storage
from corsheaders.defaults import default_headers

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"BASE_DIR in container_settings.py: {BASE_DIR}")

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Configure Google Cloud Settings
GS_BUCKET_NAME = 'pose_videos'
GS_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'gleaming-bus-449020-t9-f7d13ab90da0.json')

# Load credentials from JSON file
try:
    credentials = service_account.Credentials.from_service_account_file(
        filename=GS_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    GS_CREDENTIALS = credentials

    client = storage.Client(credentials=credentials)
    bucket = client.bucket(GS_BUCKET_NAME)
    print(f"Bucket exists: {bucket.exists()}")

    # Use the session to create a client object
    GS_CLIENT = storage.Client(credentials=credentials)

    # Use Google Cloud Storage as the default file storage
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'

    MEDIA_ROOT = ''  # GCS handles storage
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'

except FileNotFoundError:
    print(f"Error: Google Cloud credentials file not found at {GS_CREDENTIALS_PATH}")
    # You might want to set a fallback storage for local development if needed
    # DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    # MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    # MEDIA_URL = '/media/'
except Exception as e:
    print(f"Error configuring Google Cloud Storage: {e}")
    # Handle other potential exceptions


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'django', '*', '10.0.1.15', '10.0.1.16', '10.0.1.20', '10.0.1.19']
print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG', # Or 'ERROR' for production
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_app',
    'corsheaders',
    'embed_video',
    'storages'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fitness_backend.container_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fitness_backend.container_wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST', os.environ.get('POSTGRES_HOST', 'db')),
        'PORT': os.environ.get('DATABASE_PORT', os.environ.get('POSTGRES_PORT', '5432')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1:8000",
    "http://35.203.54.31",
    "http://34.118.173.89",
]

# Allow local dev frontend
CORS_ALLOWED_ORIGINS.append("http://localhost:3000")

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

AUTH_USER_MODEL = 'django_app.User'

STATIC_URL = '/static/'
MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Google Cloud Storage settings
GS_BUCKET_NAME = 'pose_videos'
GS_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'gleaming-bus-449020-t9-f7d13ab90da0.json')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}