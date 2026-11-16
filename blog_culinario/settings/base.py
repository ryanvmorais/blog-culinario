"""
Configurações compartilhadas do projeto Blog Culinário.

Reúne tudo que não muda entre ambientes (apps instalados, middleware,
templates, validação de senha, i18n). ``dev.py`` e ``prod.py`` importam este
módulo com ``from .base import *`` e sobrescrevem só o que é específico do
ambiente (DEBUG, ALLOWED_HOSTS, hardening de segurança).
"""

from __future__ import annotations

from pathlib import Path

import environ

# Raiz do projeto (onde ficam manage.py, .env e o pacote blog_culinario/).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # arquivo local, fora do git


# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------

# Chave de assinatura de sessões/CSRF. O default só serve para clonar o repo
# e rodar localmente sem configurar nada; produção define DJANGO_SECRET_KEY.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-troque-esta-chave-em-producao",
)

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])


# ---------------------------------------------------------------------------
# Apps e middleware
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # filtros de template (timesince, intcomma) das receitas
    "nucleo",
    "receitas",
    "usuarios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve estáticos sem Nginx/CDN
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "blog_culinario.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blog_culinario.demonstracao.contexto_demonstracao",
            ],
        },
    },
]

WSGI_APPLICATION = "blog_culinario.wsgi.application"


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

# SQLite por escolha — zero configuração para quem clona o repo para estudar.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Validação de senha
# ---------------------------------------------------------------------------

# Nomes de validador do Django são dotted paths longos — sem alternativa que
# caiba no line-length sem quebrar a legibilidade do dict.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"  # noqa: E501
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Arquivos estáticos e de mídia
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # destino do collectstatic (gitignored)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # uploads de imagens das receitas (gitignored)


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

LOGIN_URL = "usuarios:entrar"
LOGIN_REDIRECT_URL = "nucleo:home"
LOGOUT_REDIRECT_URL = "nucleo:home"


# ---------------------------------------------------------------------------
# Modo demonstração (spec 009)
# ---------------------------------------------------------------------------

# Desligado por padrão: quem clona tem cadastro e comentário gravando de
# verdade. A instância pública liga com MODO_DEMONSTRACAO=True, e aí cadastro
# e comentário validam mas não gravam (blog_culinario/demonstracao.py).
MODO_DEMONSTRACAO = env.bool("MODO_DEMONSTRACAO", default=False)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

# Console por padrão (nenhum requisito ainda envia email de verdade). Um
# projeto futuro com SMTP real sobrescreve isto em settings/prod.py.
MAILERS = {
    "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
}
