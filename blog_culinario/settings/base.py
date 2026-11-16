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

from blog_culinario.endereco import normalizar_url_publica

# Raiz do projeto (onde ficam manage.py, .env e o pacote blog_culinario/).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # arquivo local, fora do git


# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------

# Chave de assinatura de sessões/CSRF. O default só serve para clonar o repo
# e rodar localmente sem configurar nada; o prod.py exige DJANGO_SECRET_KEY.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-troque-esta-chave-em-producao",
)

# Desligado aqui; o dev.py liga e o prod.py mantém desligado. Não há variável
# de ambiente: o módulo de configurações escolhido já decide.
DEBUG = False

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
    "django.contrib.sitemaps",  # template do /sitemap.xml (spec 010, ADR-1)
    "nucleo",
    "receitas",
    "usuarios",
]

MIDDLEWARE = [
    # Primeiro de propósito: com ORIGEM_SEGREDO, o pedido que não veio pela
    # Cloudflare não chega a nenhuma outra camada (spec 011, RF-09).
    "blog_culinario.origem.OrigemCloudflareMiddleware",
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
                "blog_culinario.descoberta.contexto_descoberta",
            ],
        },
    },
]

WSGI_APPLICATION = "blog_culinario.wsgi.application"


# ---------------------------------------------------------------------------
# Dados graváveis (spec 011)
# ---------------------------------------------------------------------------

# Pasta do banco, da mídia enviada pelo Admin e do cache da limitação de taxa.
# Em produção, o caminho do volume que a plataforma monta e que sobrevive ao
# deploy (ex.: /data). Vazia: a raiz do repositório, como sempre foi — um
# caminho absoluto substitui o BASE_DIR, um relativo fica dentro dele, e
# Path / "" é o próprio Path.
DIRETORIO_DADOS = BASE_DIR / env.str("DIRETORIO_DADOS", default="").strip()


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

# SQLite por escolha — zero configuração para quem clona o repo para estudar.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DIRETORIO_DADOS / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Cache (spec 011)
# ---------------------------------------------------------------------------

# Em arquivo, na pasta de dados: os workers do gunicorn são processos
# separados, e um cache em memória (o LocMemCache padrão) daria a cada um o
# próprio contador da limitação de taxa. O backend do projeto torna o add() e
# o incr() atômicos entre os processos (blog_culinario/cache.py).
CACHES = {
    "default": {
        "BACKEND": "blog_culinario.cache.CacheArquivoAtomico",
        "LOCATION": DIRETORIO_DADOS / "django_cache",
    }
}


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
MEDIA_ROOT = DIRETORIO_DADOS / "media"  # capas das receitas (gitignored)


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
# Trava de origem (spec 011)
# ---------------------------------------------------------------------------

# Com um segredo definido, só passa o pedido que traz o cabeçalho
# X-Origin-Verify com ele, e o IP da limitação de taxa passa a vir do
# CF-Connecting-IP (blog_culinario/origem.py). O anterior vale junto durante
# a troca do segredo. Vazias (o padrão): trava desligada, IP do REMOTE_ADDR.
ORIGEM_SEGREDOS = tuple(
    segredo
    for segredo in (
        env.str("ORIGEM_SEGREDO", default="").strip(),
        env.str("ORIGEM_SEGREDO_ANTERIOR", default="").strip(),
    )
    if segredo
)


# ---------------------------------------------------------------------------
# Descoberta (spec 010)
# ---------------------------------------------------------------------------

# Endereço público do site, só esquema e host (https://exemplo.com.br). É a
# única fonte do canonical, do og:url, do sitemap.xml e da linha Sitemap: do
# robots.txt; vazio (o padrão em desenvolvimento) desliga os quatro. Valor
# fora do formato derruba a subida (blog_culinario/endereco.py).
URL_PUBLICA = normalizar_url_publica(env.str("URL_PUBLICA", default=""))


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

# Console por padrão (nenhum requisito ainda envia email de verdade). Um
# projeto futuro com SMTP real sobrescreve isto em settings/prod.py.
MAILERS = {
    "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
}
