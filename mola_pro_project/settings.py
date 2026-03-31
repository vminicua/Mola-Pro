"""
Django settings for mola_pro_project project.
"""

import os
from pathlib import Path

import environ  # <--- NOVO

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================
# django-environ
# ==========================
env = environ.Env(
    DEBUG=(bool, False),
)

# Lê o ficheiro .env (se existir)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ==========================
# ENVIRONMENT / DEBUG / SECRET_KEY
# ==========================
ENVIRONMENT = env("ENVIRONMENT", default="DEV")

DEBUG = env("DEBUG")  # vem como bool do .env

SECRET_KEY = env("SECRET_KEY")

# ==========================
# ALLOWED_HOSTS
# ==========================
# No .env está como string "a,b,c", aqui convertemos em lista
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost"],
)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    "admin_material.apps.AdminMaterialDashboardConfig",
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mola_pro_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

WSGI_APPLICATION = 'mola_pro_project.wsgi.application'

# ==========================
# DATABASES via .env
# ==========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env("DB_NAME"),
        'USER': env("DB_USER"),
        'PASSWORD': env("DB_PASSWORD"),
        'HOST': env("DB_HOST", default="localhost"),
        'PORT': env("DB_PORT", default="3306"),
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'  # se quiseres podemos mudar depois para Africa/Maputo
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================
# AUTENTICAÇÃO
# ==========================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "login"
