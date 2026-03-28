import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

SECRET_KEY = os.environ.get('SECRET_KEY')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Machine Learning Service
ML_SERVICE_BASE_URL = os.environ.get('ML_SERVICE_BASE_URL', 'https://www.ml.caera.my.id')

# Order guardrails
MAX_ORDER_QUANTITY = int(os.environ.get('MAX_ORDER_QUANTITY', 50))
MAX_ORDER_TOTAL_PRICE = Decimal(os.environ.get('MAX_ORDER_TOTAL_PRICE', '50000000.00'))
ORDER_CREATE_RATE_LIMIT = os.environ.get('ORDER_CREATE_RATE_LIMIT', '10/hour')

# Request/upload size guardrails
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DATA_UPLOAD_MAX_MEMORY_SIZE', 1048576))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_MEMORY_SIZE', 1048576))

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
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',

    # Local apps
    'users',
    'products',
    'orders',
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # CORS
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'backend', 'templates')],
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

WSGI_APPLICATION = 'backend.wsgi.application'

# Rest Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10, # 10 Data per halaman
    'DEFAULT_THROTTLE_RATES': {
        'order_create': ORDER_CREATE_RATE_LIMIT,
    },
}

# Simple JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'id-id' # Bahasa Indonesia
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Konfigurasi Swagger UI
SPECTACULAR_SETTINGS = {
    'TITLE': 'CaeraBouquet Backend API',
    'DESCRIPTION': 'Dokumentasi REST API resmi untuk backend Caera Bouquet.\n\nDokumentasi ini memuat endpoint autentikasi, profil pengguna, katalog produk, pemesanan, dan rekomendasi produk berbasis machine learning. Seluruh skema disusun untuk memudahkan integrasi frontend dan pengujian endpoint secara konsisten.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'CONTACT': {
        'name': 'Tim Pengembang Caera Bouquet',
    },
    'TAGS': [
        {
            'name': 'Autentikasi',
            'description': 'Endpoint untuk registrasi, login, dan pembaruan token akses.',
        },
        {
            'name': 'Pengguna',
            'description': 'Endpoint untuk mengambil informasi profil pengguna yang sedang login.',
        },
        {
            'name': 'Katalog',
            'description': 'Endpoint publik untuk melihat kategori dan produk bouquet.',
        },
        {
            'name': 'Pesanan',
            'description': 'Endpoint untuk membuat pesanan baru dan melihat riwayat pesanan pengguna.',
        },
        {
            'name': 'Rekomendasi ML',
            'description': 'Endpoint integrasi machine learning untuk memberikan rekomendasi produk.',
        },
    ],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'displayRequestDuration': True,
        'docExpansion': 'list',
    },
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        },
        'verbose': {
            'format': '%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': LOG_LEVEL,
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': LOG_LEVEL,
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'security.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'WARNING',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'app_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'app_file', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'caera': {
            'handlers': ['console', 'app_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'caera.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'users': {
            'handlers': ['console', 'app_file', 'security_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'app_file', 'security_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'products': {
            'handlers': ['console', 'app_file', 'security_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}