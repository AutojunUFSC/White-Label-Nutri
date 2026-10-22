"""Configurações base do White-Label-Nutri.

Cada empresa roda uma instância própria (banco e hospedagem separados — D-009).
Tudo que varia entre instâncias vem de variáveis de ambiente ou da
ConfiguracaoInstancia (app plataforma).
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
RAIZ_DIR = BASE_DIR.parent  # raiz do repositório
FRONTEND_DIR = RAIZ_DIR / "frontend"  # templates e estáticos

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(RAIZ_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="inseguro-somente-dev")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # lookup __unaccent das buscas
    "apps.plataforma",
    "apps.fichas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [FRONTEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.plataforma.context_processors.instancia",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@127.0.0.1:5432/nutri"),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [FRONTEND_DIR / "static"]
STATIC_ROOT = RAIZ_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Não há upload em disco: o único arquivo enviado pelo cliente é o logotipo, e ele
# fica no banco (apps/plataforma/models.py). Isso evita perder a identidade visual
# em plataformas de disco efêmero, como Heroku, Render e Fly.

# O upload de ingredientes é um TXT pequeno; o limite evita consumo de memória
# e uploads acidentais de arquivos grandes (BR-023).
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=5 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000  # o formulário de ingrediente tem ~55 campos

# PKs integer (AutoField): o schema do banco depende disso — não mudar.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LOGIN_URL = "loginUser"
LOGIN_REDIRECT_URL = "listaFichas"
LOGOUT_REDIRECT_URL = "loginUser"

# Grupo com privilégios administrativos da instância
GRUPO_ADMINISTRADORES = "administradores"

# Leitura da tabela nutricional por foto (apps/fichas/leitura_rotulo.py).
# Sem chave, o botão "Preencher a partir de foto" não aparece.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODELO = env("GEMINI_MODELO", default="gemini-3.6-flash")
# Quanto o modelo "pensa" antes de responder: minimal | low | medium | high.
# Mais raciocínio = mais lento; ler uma tabela não precisa de muito.
GEMINI_RACIOCINIO = env("GEMINI_RACIOCINIO", default="low")
GEMINI_TIMEOUT = env.float("GEMINI_TIMEOUT", default=45.0)  # segundos
LEITURA_ROTULO_MAX_BYTES = 15 * 1024 * 1024  # fotos de celular passam de 5 MB
