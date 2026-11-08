import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'insecure-secret-key-for-nhatro-management')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',

    # SOA Services (Mỗi service là 1 bounded context riêng biệt)
    'services.identity_service',
    'services.property_service',
    'services.tenant_service',
    'services.contract_service',
    'services.billing_notification_service',
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

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================================================================
# SOA DATABASE CONFIGURATION (Database per Service)
# ==============================================================================
DB_ENGINE = os.getenv('DB_ENGINE', 'mssql').lower()

if DB_ENGINE == 'mssql':
    db_trusted = os.getenv('DB_TRUSTED_CONNECTION', 'yes').lower() == 'yes'
    extra_params = 'TrustServerCertificate=yes;'
    if db_trusted:
        extra_params += 'Trusted_Connection=yes;'

    def _mssql_db_config(db_name_env, default_name):
        return {
            'ENGINE': 'mssql',
            'NAME': os.getenv(db_name_env, default_name),
            'HOST': os.getenv('DB_SERVER', r'.\SQLEXPRESS'),
            'PORT': os.getenv('DB_PORT', ''),
            'USER': os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'OPTIONS': {
                'driver': os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server'),
                'extra_params': extra_params,
            },
        }

    DATABASES = {
        'default': _mssql_db_config('DB_NAME_IDENTITY', 'nhatro_identity_db'),
        'property_db': _mssql_db_config('DB_NAME_PROPERTY', 'nhatro_property_db'),
        'tenant_db': _mssql_db_config('DB_NAME_TENANT', 'nhatro_tenant_db'),
        'contract_db': _mssql_db_config('DB_NAME_CONTRACT', 'nhatro_contract_db'),
        'billing_db': _mssql_db_config('DB_NAME_BILLING', 'nhatro_billing_db'),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_identity.sqlite3',
        },
        'property_db': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_property.sqlite3',
        },
        'tenant_db': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_tenant.sqlite3',
        },
        'contract_db': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_contract.sqlite3',
        },
        'billing_db': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_billing.sqlite3',
        },
    }

# SOA Database Router
DATABASE_ROUTERS = ['config.db_router.ServiceDatabaseRouter']

# Custom User Model (Nằm trong Identity Service)
AUTH_USER_MODEL = 'identity_service.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'vi-vn'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# SimpleJWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# OpenAPI / Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Quản Lý Nhà Trọ API - SOA Microservices Architecture',
    'DESCRIPTION': 'Sprint 1: Identity Service (Auth & RBAC), Property Service (House & Room Management)',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
