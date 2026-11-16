"""
Configuração raiz de URLs do projeto Blog Culinário.

Mapeia as rotas principais: painel Admin do Django, e as URLs de cada app de
domínio (``nucleo``, ``receitas``, ``usuarios``), cada um com seu próprio
namespace via ``app_name`` em ``urls.py``. Os arquivos de descoberta
(``robots.txt``, ``sitemap.xml`` e ``/.well-known/security.txt``, spec 010)
ficam aqui, sem namespace, porque são caminhos fixos da raiz do site.

A rota de ``media/`` serve as capas das receitas pelo próprio Django, com ou
sem ``DEBUG`` (``nucleo.views.servir_midia``, spec 011): o WhiteNoise cuida só
dos estáticos, e a plataforma de deploy não tem servidor web na frente.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from blog_culinario import descoberta
from nucleo.views import servir_midia
from receitas.sitemaps import ReceitaSitemap
from usuarios.views import entrar_no_admin

# Montado aqui, e não em descoberta.py, para aquele módulo não importar de
# receitas (o padrão da documentação do Django para o framework de sitemaps).
SITEMAPS = {"paginas": descoberta.PaginasSitemap, "receitas": ReceitaSitemap}

urlpatterns: list[URLPattern | URLResolver] = [
    # Antes do admin.site.urls, para o login do Admin passar pelo limite de
    # tentativas do login do site (usuarios.views.entrar_no_admin).
    path("admin/login/", entrar_no_admin, name="admin_login_limitado"),
    path("admin/", admin.site.urls),
    path("robots.txt", descoberta.robots_txt, name="robots_txt"),
    path(
        "sitemap.xml",
        descoberta.sitemap,
        {"sitemaps": SITEMAPS},
        name="sitemap",
    ),
    path(
        ".well-known/security.txt",
        descoberta.security_txt,
        name="security_txt",
    ),
    path("", include("nucleo.urls")),
    path("receitas/", include("receitas.urls")),
    path("usuarios/", include("usuarios.urls")),
    # O MEDIA_URL começa com "/", que o path() não aceita no início.
    path(
        f"{settings.MEDIA_URL.lstrip('/')}<path:caminho>",
        servir_midia,
        name="midia",
    ),
]
