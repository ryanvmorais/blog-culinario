"""
Configuração raiz de URLs do projeto Blog Culinário.

Mapeia as rotas principais: painel Admin do Django, e as URLs de cada app de
domínio (``nucleo``, ``receitas``, ``usuarios``), cada um com seu próprio
namespace via ``app_name`` em ``urls.py``. Os arquivos de descoberta
(``robots.txt``, ``sitemap.xml`` e ``/.well-known/security.txt``, spec 010)
ficam aqui, sem namespace, porque são caminhos fixos da raiz do site.

Em desenvolvimento (``DEBUG=True``), acrescenta a rota de ``media/`` para
servir os uploads de imagem das receitas diretamente pelo Django — em
produção, o WhiteNoise cuida só de estáticos, e mídia real usaria um
storage externo (fora do escopo deste projeto educacional).
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from blog_culinario import descoberta
from receitas.sitemaps import ReceitaSitemap

# Montado aqui, e não em descoberta.py, para aquele módulo não importar de
# receitas (o padrão da documentação do Django para o framework de sitemaps).
SITEMAPS = {"paginas": descoberta.PaginasSitemap, "receitas": ReceitaSitemap}

urlpatterns: list[URLPattern | URLResolver] = [
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
]

if settings.DEBUG:
    # Em produção o WhiteNoise/servidor web cuida disso; em dev o Django serve
    # media/ diretamente para não exigir configuração extra de quem clona o repo.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
