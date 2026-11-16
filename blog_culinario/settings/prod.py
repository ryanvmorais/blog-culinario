"""
Configurações de produção — alvo de deploy: Railway, atrás da Cloudflare.

Ativado via ``DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod``, que a
receita de build (``railpack.json``) define em cada comando e que o ``wsgi.py``
usa como padrão (spec 011, ADR-2). Exige ``SECRET_KEY`` (lida no ``base.py``,
obrigatória em todo ambiente) e ``ALLOWED_HOSTS`` (ver ``.env.example``).
"""

from __future__ import annotations

from .base import *  # noqa: F403 — reexporta as configurações compartilhadas
from .base import env

DEBUG = False

# Ex.: "blog.exemplo.com.br" — obrigatório, sem default permissivo: ausente, a
# subida falha; vazio, todo host é recusado. Espaços e vírgula sobrando não
# viram host (spec 011, RF-05).
ALLOWED_HOSTS = [host.strip() for host in env.list("ALLOWED_HOSTS") if host.strip()]

# Estáticos comprimidos e versionados por hash — o WhiteNoiseMiddleware (já
# ativo via base.py) serve tudo direto do processo Django, sem servidor de
# arquivos estáticos separado. O manifesto (staticfiles.json) sai do
# collectstatic do build, rodado com estas configurações.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Hardening padrão para rodar atrás de HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Atrás do proxy da plataforma o TLS termina antes do Django, que recebe HTTP.
# O proxy avisa o protocolo original neste cabeçalho; sem lê-lo, o
# SECURE_SSL_REDIRECT redireciona para sempre. Num servidor que entrega o
# Django direto à internet, sem proxy, tire esta linha: o cliente poderia
# mandar o cabeçalho e pular o redirect (spec 011, RF-03).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# 1 semana para começar; suba para 31536000 (1 ano) só depois de confirmar
# que todo o site serve HTTPS sem exceção — HSTS não tem "desfazer" rápido.
SECURE_HSTS_SECONDS = 604_800
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

# O LOGGING padrão do Django só manda o erro 500 por e-mail aos ADMINS, que o
# projeto não define: sem isto, o erro não aparece no log do serviço, que a
# plataforma monta com a saída de erro do processo (spec 011, RF-11).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    # 404 e 403 saem como WARNING no django.request; ERROR deixa só o 500 (os
    # robôs que testam caminhos o dia inteiro não afogam o erro real).
    "loggers": {"django.request": {"level": "ERROR"}},
}

# O blog não envia e-mail (spec 011, decisão resolvida 8): o backend de console
# do base.py só existe porque o Django exige um, e o check --deploy o acusa
# (mail.E001). Uma funcionalidade que passe a enviar e-mail configura o SMTP
# no MAILERS daqui e tira esta linha.
SILENCED_SYSTEM_CHECKS = ["mail.E001"]
