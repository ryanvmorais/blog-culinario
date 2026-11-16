"""
Descoberta pelos buscadores e pelas redes sociais (spec 010).

Reúne o que diz ao buscador onde está cada página: o context processor do
endereço canônico, os sitemaps e as views de ``robots.txt``, ``sitemap.xml`` e
``/.well-known/security.txt``. Todo endereço absoluto sai de ``URL_PUBLICA``,
por ``url_absoluta``; nada aqui confia no ``Host`` do pedido (RNF-03).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps import views as views_sitemaps
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.encoding import escape_uri_path
from django.views.decorators.http import require_safe

from blog_culinario.demonstracao import URL_REPOSITORIO, modo_demonstracao_ligado
from blog_culinario.endereco import url_absoluta

# Prazo do contato de segurança (RFC 9116). Fixo de propósito: um teste falha
# 30 dias antes, e o PR que move a data é a hora de conferir se o contato
# ainda é cuidado (ADR-6 da spec 010).
EXPIRACAO_SECURITY_TXT = "2027-11-01T00:00:00Z"

_TEXTO_PURO = "text/plain; charset=utf-8"

# ---------------------------------------------------------------------------
# Endereço canônico
# ---------------------------------------------------------------------------

# Única página cujo canonical leva parâmetro: a página 2 da lista tem
# receitas que a 1 não tem. Busca e filtros ficam de fora (decisão
# resolvida 3 da spec 010).
_ROTA_PAGINADA = "receitas:lista"


def _pagina_da_lista(request: HttpRequest) -> int:
    """
    Lê o número da página da lista de receitas, se o pedido for para ela.

    Args:
        request (HttpRequest): requisição atual.

    Returns:
        int: o ``page`` da query quando é um inteiro e o pedido resolveu para
        a lista; 1 em qualquer outro caso (``?page=last`` inclusive, ADR-3).
    """
    rota = request.resolver_match
    if rota is None or rota.view_name != _ROTA_PAGINADA:
        return 1
    pagina = request.GET.get("page", "")
    return int(pagina) if pagina.isdecimal() else 1


def contexto_descoberta(request: HttpRequest) -> dict[str, str]:
    """
    Entrega aos templates o endereço canônico da página (ADR-3 da spec 010).

    O caminho vem do pedido e o endereço, de ``URL_PUBLICA``; a query string
    fica de fora, menos o ``page`` da lista. As páginas de erro esvaziam o
    bloco que usa a variável, então ela pode existir num 404.

    Args:
        request (HttpRequest): requisição atual.

    Returns:
        dict[str, str]: ``url_canonica``, vazia sem ``URL_PUBLICA``.
    """
    url = url_absoluta(escape_uri_path(request.path))
    if url:
        pagina = _pagina_da_lista(request)
        if pagina > 1:
            url = f"{url}?page={pagina}"
    return {"url_canonica": url}


# ---------------------------------------------------------------------------
# Sitemaps
# ---------------------------------------------------------------------------


# O Sitemap é genérico só nos stubs; em runtime, Sitemap[Any] levantaria TypeError.
class SitemapPublico(Sitemap):  # type: ignore[type-arg]
    """
    Sitemap com domínio e protocolo de ``URL_PUBLICA`` (ADR-1 da spec 010).

    A view do Django passa um ``RequestSite`` montado a partir do ``Host`` do
    pedido; os dois métodos abaixo o ignoram, para todo ``<loc>`` sair do
    endereço configurado (RNF-03).
    """

    def get_protocol(self, protocol: str | None = None) -> str:
        """
        Devolve o esquema de ``URL_PUBLICA``.

        Args:
            protocol (str | None, optional): esquema do pedido, ignorado.
                Padrão: ``None``.

        Returns:
            str: ``http`` ou ``https``.
        """
        return urlsplit(settings.URL_PUBLICA).scheme

    def get_domain(self, site: Any = None) -> str:
        """
        Devolve o host (com a porta, se houver) de ``URL_PUBLICA``.

        Args:
            site (Any, optional): ``Site`` ou ``RequestSite`` da view, ignorado.
                Padrão: ``None``.

        Returns:
            str: o host de ``URL_PUBLICA``.
        """
        return urlsplit(settings.URL_PUBLICA).netloc


class PaginasSitemap(SitemapPublico):
    """Páginas fixas do sitemap: a home e a lista de receitas (RF-05)."""

    def items(self) -> list[str]:
        """
        Nomes das rotas das páginas fixas.

        Returns:
            list[str]: nomes de rota, na ordem em que aparecem no sitemap.
        """
        return ["nucleo:home", "receitas:lista"]

    def location(self, item: str) -> str:
        """
        Caminho de uma página fixa.

        Args:
            item (str): nome da rota.

        Returns:
            str: o caminho, sem query string.
        """
        return reverse(item)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def _texto(linhas: list[str]) -> HttpResponse:
    """
    Responde as linhas como texto puro, uma por linha (ADR-4 da spec 010).

    Args:
        linhas (list[str]): linhas do arquivo, sem o fim de linha.

    Returns:
        HttpResponse: 200, ``text/plain; charset=utf-8``.
    """
    return HttpResponse("\n".join(linhas) + "\n", content_type=_TEXTO_PURO)


@require_safe
def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Serve o ``/robots.txt`` (RF-04).

    O Admin fica de fora do rastreio; o caminho é o padrão do Django e não é
    segredo (decisão resolvida 6). Login e cadastro continuam rastreáveis,
    porque o Lighthouse CI os audita.

    Args:
        request (HttpRequest): requisição atual.

    Returns:
        HttpResponse: o arquivo, com a linha ``Sitemap:`` só com ``URL_PUBLICA``.
    """
    linhas = ["User-agent: *", "Disallow: /admin/"]
    url_sitemap = url_absoluta(reverse("sitemap"))
    if url_sitemap:
        linhas += ["", f"Sitemap: {url_sitemap}"]
    return _texto(linhas)


@require_safe
def sitemap(
    request: HttpRequest, sitemaps: dict[str, type[Sitemap[Any]] | Sitemap[Any]]
) -> HttpResponse:
    """
    Serve o ``/sitemap.xml`` pela view do Django (RF-05, ADR-1).

    Args:
        request (HttpRequest): requisição atual.
        sitemaps (dict[str, type[Sitemap[Any]] | Sitemap[Any]]): seções do
            sitemap, passadas pela rota.

    Returns:
        HttpResponse: o XML do sitemap.

    Raises:
        Http404: sem ``URL_PUBLICA``; o sitemap não é montado a partir do
            ``Host``.
    """
    if not settings.URL_PUBLICA:
        raise Http404("Sitemap indisponível sem URL_PUBLICA.")
    resposta: HttpResponse = views_sitemaps.sitemap(request, sitemaps=sitemaps)
    return resposta


@require_safe
def security_txt(request: HttpRequest) -> HttpResponse:
    """
    Serve o ``/.well-known/security.txt`` da demonstração (RF-06, RFC 9116).

    Só existe com o modo demonstração: o contato é o do repositório do
    projeto, e num deploy que não é a demo ele apontaria para quem não
    responde por aquele site (decisão resolvida 4).

    Args:
        request (HttpRequest): requisição atual.

    Returns:
        HttpResponse: o arquivo, com ``Canonical:`` só com ``URL_PUBLICA``.

    Raises:
        Http404: com o modo demonstração desligado.
    """
    if not modo_demonstracao_ligado():
        raise Http404("security.txt só existe na instância de demonstração.")
    linhas = [
        f"Contact: {URL_REPOSITORIO}/security/advisories/new",
        f"Expires: {EXPIRACAO_SECURITY_TXT}",
        "Preferred-Languages: pt, en",
        f"Policy: {URL_REPOSITORIO}/blob/main/SECURITY.md",
    ]
    canonical = url_absoluta(reverse("security_txt"))
    if canonical:
        linhas.append(f"Canonical: {canonical}")
    return _texto(linhas)
