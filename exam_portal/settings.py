"""
Django settings for Exam Portal.

Professional online examination system with role-based access control.

For more information on Django settings, see:
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

from pathlib import Path
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-ek*dm9e*_b)y9*8qoi!g$0x7kz5ti4qt=$p6*s3ww^1i+n_kmq')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost',]


# Application definition

INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Core functionality
    'core',            # Reusable utilities, base models, mixins
    'accounts',        # User model and authentication
    'questions',       # Question bank and individual submissions
    'exams',           # Tests, attempts, grading, certificates
    
    # Role-specific modules (views and templates only)
    'students',        # Student-facing functionality
    'teachers',        # Teacher-facing functionality
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'exam_portal.middleware.LocalhostRedirectMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'exam_portal.middleware.BlockedUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'exam_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notification_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'exam_portal.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#database# if os.environ.get('DATABASE_URL'):
#     DATABASES = {
#         'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600)
#     }
# else:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'online_exam_db',
        'USER': 'anujpal',
        'PASSWORD': 'p0o9i8u7',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
# Password validation
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'  # Indian Standard Time (IST, UTC+5:30)

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = 'static/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Media (user-uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'
# Authentication redirects
# Ensure login-required views redirect to your login URL instead of the default '/accounts/login/'
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/auth/dashboard/student/'

# Email configuration
# For development, use console backend (instant, no SMTP delay)
# For production, use SMTP backend and override via environment variables
# 
# To see emails in console during development, set:
# EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
#
# For production with actual email sending:
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'sout.anujpal@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'ppirnmtyjqedsvxb')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@online-exam.local')

# Connection timeout settings for faster email failure detection (in seconds)
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 10))  # 10 seconds max per connection

# Site configuration for emails
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')
# SITE_DOMAIN = os.environ.get('SITE_DOMAIN') 
USE_HTTPS = os.environ.get('USE_HTTPS', 'False').lower() == 'true'

# Password reset token timeout (in seconds). Default ~3 days if unset.
from django.conf import global_settings as _gs
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT', getattr(_gs, 'PASSWORD_RESET_TIMEOUT', 259200)))

