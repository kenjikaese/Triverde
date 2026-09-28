"""
Configuracion de Django para el backend de Triverde (Incremento 1).

Stack: Django + DRF + PostgreSQL (docs/05). La configuracion se lee de variables
de entorno (12-factor): en Docker vienen del docker-compose; en local, de un .env.
Fallback a SQLite si no hay DATABASE_URL, para poder correr sin Docker.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOW_ALL=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-secret-key-cambiar")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Modulos del sistema (Incremento 1)
    "common",
    "acceso",          # Modulo 1 - Acceso y auditoria
    "configuracion",   # Modulo 2 - Configuracion
    "mantenedores",    # Modulo 3 - Mantenedores
    "recepcion",       # Modulo 4 - Recepcion
    # Modulos del sistema (Incremento 2)
    "inventario",      # Modulo 5 - Inventario, pilas y procesos
    "mezcla",          # Modulo 6 - Mezcla y alertas (Alerta compartida con M11)
    "proyecciones",    # Modulo 7 - Proyecciones
    "comercial",       # Modulo 8 - Comercial
    "mantenimiento",   # Modulo 11 - Mantenimiento
    "reportes",        # Modulo 10 - Reportes y panel (Parte C)
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos (RNF-02: relacional) -------------------------------------
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    ),
}

# --- Usuario custom (docs/11 - Usuario extiende AbstractUser) ---------------
AUTH_USER_MODEL = "acceso.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalizacion ---------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# --- Archivos estaticos y media ---------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF --------------------------------------------------------------------
# Token de DRF para la PWA (guarda el token para operar offline); sesion para
# el Browsable API en desarrollo.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# --- CORS (la PWA consumira la API desde otro origen) -----------------------
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL")

# --- Trazas de seguimiento por caso de uso ----------------------------------
# El logger `triverde.cu` registra el paso por los puntos de negocio (ver
# common/trazas.py). Con TRIVERDE_TRAZAS=1 escribe ademas a logs/trazas-cu.log,
# que es lo que leen las pruebas end-to-end para verificar que la operacion
# paso por el servidor. Apagado por defecto: en produccion no se crea archivo.
TRAZAS_ACTIVAS = env.bool("TRIVERDE_TRAZAS", default=False)
TRAZAS_ARCHIVO = BASE_DIR / "logs" / "trazas-cu.log"

if TRAZAS_ACTIVAS:
    TRAZAS_ARCHIVO.parent.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "traza": {"format": "%(asctime)s %(message)s"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "traza",
        },
        **(
            {
                "archivo_trazas": {
                    "class": "logging.FileHandler",
                    "filename": str(TRAZAS_ARCHIVO),
                    "encoding": "utf-8",
                    "formatter": "traza",
                }
            }
            if TRAZAS_ACTIVAS
            else {}
        ),
    },
    "loggers": {
        "triverde.cu": {
            "handlers": ["consola"] + (["archivo_trazas"] if TRAZAS_ACTIVAS else []),
            "level": "INFO",
            "propagate": False,
        },
    },
}
