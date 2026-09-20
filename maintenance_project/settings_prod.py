import os
from .settings import *

# Configurações de Segurança
DEBUG = True  # Temporariamente True para debug
SECRET_KEY = 'django-insecure-sua-chave-secreta-muito-segura-123'  # Temporário para desenvolvimento
ALLOWED_HOSTS = ['*']  # Permite todos os hosts durante o desenvolvimento

# Configurações do Banco de Dados
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'sistema_familiar_db'),
        'USER': os.environ.get('POSTGRES_USER', 'sistema_familiar_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'SenhaSegura2024'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 5,
            'client_encoding': 'UTF8',
            'sslmode': 'disable',
        }
    }
}

# Configurações de Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Configurações de Arquivos Estáticos
STATIC_ROOT = '/app/staticfiles'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configurações de Media
MEDIA_ROOT = '/app/media'
MEDIA_URL = '/media/'

# Configurações de Segurança Adicionais
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Configurações de Sessão e Cookies
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configuração do Whitenoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Configuração de Mensagens
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Configurações de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
} 