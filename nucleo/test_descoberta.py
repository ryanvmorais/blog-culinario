"""
Testes da descoberta pelos buscadores e pelas redes sociais (spec 010).

Cobrem a validação de ``URL_PUBLICA``, o canonical e as tags Open Graph do
``<head>``, e os três arquivos de descoberta (``robots.txt``, ``sitemap.xml`` e
``security.txt``). O endereço absoluto nunca pode vir do ``Host`` do pedido
(RNF-03): por isso os pedidos usam um ``HTTP_HOST`` diferente do host de
``URL_PUBLICA``, e o teste confere que só o segundo aparece.

Estratégia de isolamento: ORM e HTTP de teste do Django, sem mock nem rede;
``override_settings`` liga ``URL_PUBLICA`` e o modo demonstração por teste.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone
from django.views.defaults import permission_denied

from blog_culinario.demonstracao import URL_REPOSITORIO
from blog_culinario.descoberta import EXPIRACAO_SECURITY_TXT, contexto_descoberta
from blog_culinario.endereco import normalizar_url_publica, url_absoluta
from receitas.models import Categoria, Receita

URL_PUBLICA_TESTE = "https://blog.exemplo.com.br"

# Host aceito pelo settings de desenvolvimento e diferente do de URL_PUBLICA:
# se ele aparecer num endereço absoluto, o endereço veio do pedido (RNF-03).
HOST_DO_PEDIDO = "localhost"

NS_SITEMAP = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------


def _receita(
    titulo: str = "Bolo de cenoura",
    categoria: Categoria | None = None,
    publicado: bool = True,
) -> Receita:
    """
    Cria uma receita mínima.

    Args:
        titulo (str, optional): título da receita. Padrão: ``"Bolo de cenoura"``.
        categoria (Categoria | None, optional): categoria já existente; sem ela,
            cria (ou reaproveita) "Sobremesas". Padrão: ``None``.
        publicado (bool, optional): se a receita aparece nas views públicas.
            Padrão: ``True``.

    Returns:
        Receita: instância persistida.
    """
    if categoria is None:
        categoria = Categoria.objects.filter(
            slug="sobremesas"
        ).first() or Categoria.objects.create(nome="Sobremesas")
    return Receita.objects.create(
        titulo=titulo,
        resumo=f"Resumo de {titulo}.",
        ingredientes="1 ingrediente",
        modo_de_preparo="Misture tudo.",
        tempo_preparo_minutos=10,
        porcoes=1,
        categoria=categoria,
        publicado=publicado,
    )


def _html(client: Client, caminho: str, status: int = 200) -> str:
    """
    Pede uma página com o ``Host`` de teste e devolve o HTML.

    Args:
        client (Client): client de teste do Django.
        caminho (str): caminho com a query string, se houver.
        status (int, optional): status esperado. Padrão: ``200``.

    Returns:
        str: o HTML da resposta.
    """
    resposta = client.get(caminho, HTTP_HOST=HOST_DO_PEDIDO)
    assert resposta.status_code == status
    return resposta.content.decode()


def _canonical(pagina: str) -> str | None:
    """
    Lê o ``href`` do ``<link rel="canonical">``.

    Args:
        pagina (str): HTML da página.

    Returns:
        str | None: o endereço, ou ``None`` se não houver canonical.
    """
    achado = re.search(r'<link rel="canonical" href="([^"]*)"', pagina)
    return html.unescape(achado.group(1)) if achado else None


def _meta(pagina: str, atributo: str, nome: str) -> str | None:
    """
    Lê o ``content`` de uma ``<meta>`` pelo ``name`` ou pelo ``property``.

    Args:
        pagina (str): HTML da página.
        atributo (str): ``"name"`` ou ``"property"``.
        nome (str): valor do atributo, como ``"og:url"``.

    Returns:
        str | None: o conteúdo, ou ``None`` se a tag não existir.
    """
    padrao = rf'<meta {atributo}="{re.escape(nome)}" content="([^"]*)"'
    achado = re.search(padrao, pagina)
    return html.unescape(achado.group(1)) if achado else None


def _titulo(pagina: str) -> str:
    """
    Lê o texto do ``<title>``.

    Args:
        pagina (str): HTML da página.

    Returns:
        str: o título, com as entidades HTML resolvidas.
    """
    achado = re.search(r"<title>(.*?)</title>", pagina, re.S)
    assert achado is not None
    return html.unescape(achado.group(1))


# ---------------------------------------------------------------------------
# URL_PUBLICA (RF-01)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("", ""),
        ("   ", ""),
        ("https://exemplo.com.br", "https://exemplo.com.br"),
        ("https://exemplo.com.br/", "https://exemplo.com.br"),
        ("  https://exemplo.com.br/  ", "https://exemplo.com.br"),
        ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
        ("http://localhost:8000/", "http://localhost:8000"),
    ],
)
def test_url_publica_valida_e_normalizada(valor: str, esperado: str) -> None:
    assert normalizar_url_publica(valor) == esperado


@pytest.mark.parametrize(
    "valor",
    [
        "exemplo.com.br",
        "//exemplo.com.br",
        "ftp://exemplo.com.br",
        "https://",
        "https://exemplo.com.br/blog",
        "https://exemplo.com.br/?q=1",
        "https://exemplo.com.br?",
        "https://exemplo.com.br/#topo",
        "https://exemplo.com.br#",
        "https://usuario@exemplo.com.br",
        "https://usuario:senha@exemplo.com.br",
        "https://exemplo.com.br:porta",
        "https://exemplo.com.br:99999",
    ],
)
def test_url_publica_invalida_derruba_a_subida(valor: str) -> None:
    with pytest.raises(ImproperlyConfigured, match="URL_PUBLICA"):
        normalizar_url_publica(valor)


@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_url_absoluta_parte_da_url_publica() -> None:
    assert url_absoluta("/receitas/") == f"{URL_PUBLICA_TESTE}/receitas/"


@override_settings(URL_PUBLICA="")
def test_url_absoluta_vazia_sem_url_publica() -> None:
    assert url_absoluta("/receitas/") == ""


# ---------------------------------------------------------------------------
# Canonical e og:url (RF-02, RNF-03)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
@pytest.mark.parametrize(
    "caminho", ["/", "/receitas/", "/usuarios/entrar/", "/usuarios/cadastro/"]
)
def test_canonical_e_og_url_vem_so_da_url_publica(client: Client, caminho: str) -> None:
    pagina = _html(client, f"{caminho}?utm_source=teste&next=/x/")

    assert _canonical(pagina) == f"{URL_PUBLICA_TESTE}{caminho}"
    assert _meta(pagina, "property", "og:url") == f"{URL_PUBLICA_TESTE}{caminho}"
    assert HOST_DO_PEDIDO not in (_canonical(pagina) or "")


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_canonical_do_detalhe_da_receita(client: Client) -> None:
    receita = _receita()
    caminho = reverse("receitas:detalhe", kwargs={"slug": receita.slug})

    pagina = _html(client, caminho)

    assert _canonical(pagina) == f"{URL_PUBLICA_TESTE}{caminho}"


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_canonical_da_lista_guarda_so_a_pagina(client: Client) -> None:
    """Decisão resolvida 3: busca e filtros saem; a página 2 tem endereço próprio."""
    for numero in range(10):  # paginate_by = 9: a décima receita vai à página 2
        _receita(f"Bolo {numero}")

    segunda = _html(client, "/receitas/?page=2&q=bolo&categoria=sobremesas")
    primeira = _html(client, "/receitas/?page=1&q=bolo")

    assert _canonical(segunda) == f"{URL_PUBLICA_TESTE}/receitas/?page=2"
    assert _canonical(primeira) == f"{URL_PUBLICA_TESTE}/receitas/"


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_page_fora_da_lista_nao_entra_no_canonical(client: Client) -> None:
    pagina = _html(client, "/?page=2")

    assert _canonical(pagina) == f"{URL_PUBLICA_TESTE}/"


@pytest.mark.django_db
@override_settings(URL_PUBLICA="")
def test_sem_url_publica_nao_ha_canonical_nem_og_url(client: Client) -> None:
    pagina = _html(client, "/receitas/")

    assert _canonical(pagina) is None
    assert _meta(pagina, "property", "og:url") is None


@pytest.mark.django_db
@override_settings(URL_PUBLICA="")
def test_sem_url_publica_a_pagina_2_tambem_fica_sem_canonical(client: Client) -> None:
    # Sem o endereço, o ?page=2 não pode virar um canonical relativo sozinho.
    for numero in range(10):  # paginate_by = 9: a décima receita vai à página 2
        _receita(f"Bolo {numero}")

    pagina = _html(client, "/receitas/?page=2")

    assert _canonical(pagina) is None


@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_canonical_sai_com_o_caminho_codificado(rf: RequestFactory) -> None:
    pedido = rf.get("/receitas/pão de ló/")

    assert contexto_descoberta(pedido) == {
        "url_canonica": f"{URL_PUBLICA_TESTE}/receitas/p%C3%A3o%20de%20l%C3%B3/"
    }


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_404_de_receita_nao_publicada_nao_tem_canonical(client: Client) -> None:
    receita = _receita(publicado=False)
    caminho = reverse("receitas:detalhe", kwargs={"slug": receita.slug})

    pagina = _html(client, caminho, 404)

    assert _canonical(pagina) is None
    assert _meta(pagina, "property", "og:url") is None


@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_403_nao_tem_canonical(rf: RequestFactory) -> None:
    resposta = permission_denied(rf.get("/receitas/"), PermissionError())

    assert _canonical(resposta.content.decode()) is None


# ---------------------------------------------------------------------------
# Open Graph sem imagem (RF-03, RF-07)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("caminho", "tipo"),
    [
        ("/", "website"),
        ("/receitas/", "website"),
        ("/usuarios/entrar/", "website"),
        ("/usuarios/cadastro/", "website"),
        (None, "article"),  # detalhe da receita, criada no teste
    ],
)
def test_open_graph_repete_titulo_e_descricao(
    client: Client, caminho: str | None, tipo: str
) -> None:
    if caminho is None:
        caminho = reverse("receitas:detalhe", kwargs={"slug": _receita().slug})

    pagina = _html(client, caminho)

    assert _meta(pagina, "property", "og:title") == _titulo(pagina)
    assert _meta(pagina, "property", "og:description") == _meta(
        pagina, "name", "description"
    )
    assert _meta(pagina, "property", "og:type") == tipo
    assert _meta(pagina, "property", "og:site_name") == "Blog Culinário"
    assert _meta(pagina, "property", "og:locale") == "pt_BR"
    assert "og:image" not in pagina
    assert "twitter:" not in pagina


@pytest.mark.django_db
def test_titulo_com_caractere_especial_escapado_uma_vez(client: Client) -> None:
    """ADR-2: o texto capturado já sai escapado e não é escapado de novo."""
    receita = _receita('Pão "caseiro" & manteiga')
    caminho = reverse("receitas:detalhe", kwargs={"slug": receita.slug})

    pagina = _html(client, caminho)

    assert "&amp;amp;" not in pagina
    assert _titulo(pagina).startswith('Pão "caseiro" & manteiga')
    assert _meta(pagina, "property", "og:title") == _titulo(pagina)


@pytest.mark.django_db
@override_settings(URL_PUBLICA="")
def test_head_sem_url_publica_segue_o_de_antes(client: Client) -> None:
    """RF-07: fora das og:*, o <head> da home tem o título e a descrição de antes."""
    pagina = _html(client, "/")

    assert _titulo(pagina) == "Blog Culinário — receitas para todos os dias"
    assert _meta(pagina, "name", "description") == (
        "Receitas simples para todos os dias, com comentários da comunidade. "
        "Por dentro, um projeto Django educacional e aberto."
    )
    assert pagina.count("<title>") == 1
    assert pagina.count('name="description"') == 1


# ---------------------------------------------------------------------------
# robots.txt (RF-04)
# ---------------------------------------------------------------------------


def _linhas(client: Client, caminho: str) -> list[str]:
    """
    Pede um arquivo de texto e devolve as linhas, conferindo status e tipo.

    Args:
        client (Client): client de teste do Django.
        caminho (str): caminho do arquivo.

    Returns:
        list[str]: as linhas do corpo, sem o fim de linha.
    """
    resposta = client.get(caminho, HTTP_HOST=HOST_DO_PEDIDO)
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "text/plain; charset=utf-8"
    linhas: list[str] = resposta.content.decode().splitlines()
    return linhas


@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_robots_txt_com_url_publica(client: Client) -> None:
    assert _linhas(client, "/robots.txt") == [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {URL_PUBLICA_TESTE}/sitemap.xml",
    ]


@override_settings(URL_PUBLICA="")
def test_robots_txt_sem_url_publica_nao_tem_sitemap(client: Client) -> None:
    assert _linhas(client, "/robots.txt") == ["User-agent: *", "Allow: /"]


def test_robots_txt_nao_cita_o_caminho_do_admin(client: Client) -> None:
    # Um Disallow com o caminho entregaria o ADMIN_URL trocado (spec 011, RF-14).
    corpo = client.get("/robots.txt", HTTP_HOST=HOST_DO_PEDIDO).content.decode()
    assert "admin" not in corpo.lower()


def test_login_do_admin_pede_para_nao_ser_indexado(client: Client) -> None:
    # É o que deixa o robots.txt sem citar o Admin (decisão resolvida 6).
    resposta = client.get(reverse("admin:login"), HTTP_HOST=HOST_DO_PEDIDO)
    assert re.search(
        r'<meta name="robots" content="[^"]*NONE', resposta.content.decode()
    )


# ---------------------------------------------------------------------------
# sitemap.xml (RF-05, RNF-03)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_sitemap_lista_home_lista_e_so_receitas_publicadas(client: Client) -> None:
    publicada = _receita("Bolo de cenoura")
    _receita("Rascunho de torta", publicado=False)

    resposta = client.get("/sitemap.xml", HTTP_HOST=HOST_DO_PEDIDO)
    raiz = ET.fromstring(resposta.content)
    entradas = {
        url.findtext("s:loc", namespaces=NS_SITEMAP): url.findtext(
            "s:lastmod", namespaces=NS_SITEMAP
        )
        for url in raiz.findall("s:url", NS_SITEMAP)
    }
    detalhe = reverse("receitas:detalhe", kwargs={"slug": publicada.slug})

    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "application/xml"
    assert raiz.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"
    # O template do sitemap escreve a data no fuso do site (TIME_ZONE), e o
    # atualizado_em vem em UTC: das 21h à meia-noite de Brasília, as duas
    # datas já são dias diferentes.
    data_local = timezone.localdate(publicada.atualizado_em).isoformat()
    assert entradas == {
        f"{URL_PUBLICA_TESTE}/": None,
        f"{URL_PUBLICA_TESTE}/receitas/": None,
        f"{URL_PUBLICA_TESTE}{detalhe}": data_local,
    }
    assert HOST_DO_PEDIDO.encode() not in resposta.content


@pytest.mark.django_db
@override_settings(URL_PUBLICA=URL_PUBLICA_TESTE)
def test_cada_loc_do_sitemap_e_o_canonical_da_pagina(client: Client) -> None:
    _receita()

    raiz = ET.fromstring(client.get("/sitemap.xml", HTTP_HOST=HOST_DO_PEDIDO).content)
    locs = [loc.text or "" for loc in raiz.iterfind("s:url/s:loc", NS_SITEMAP)]

    assert locs
    for loc in locs:
        caminho = loc.removeprefix(URL_PUBLICA_TESTE)
        assert _canonical(_html(client, caminho)) == loc


@pytest.mark.django_db
@override_settings(URL_PUBLICA="")
def test_sitemap_sem_url_publica_responde_404(client: Client) -> None:
    resposta = client.get("/sitemap.xml", HTTP_HOST=HOST_DO_PEDIDO)

    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# security.txt (RF-06, ADR-6)
# ---------------------------------------------------------------------------


@override_settings(MODO_DEMONSTRACAO=True, URL_PUBLICA=URL_PUBLICA_TESTE)
def test_security_txt_na_demonstracao(client: Client) -> None:
    linhas = _linhas(client, "/.well-known/security.txt")
    campos = dict(linha.split(": ", 1) for linha in linhas)

    assert campos == {
        "Contact": f"{URL_REPOSITORIO}/security/advisories/new",
        "Expires": EXPIRACAO_SECURITY_TXT,
        "Preferred-Languages": "pt, en",
        "Policy": f"{URL_REPOSITORIO}/blob/main/SECURITY.md",
        "Canonical": f"{URL_PUBLICA_TESTE}/.well-known/security.txt",
    }
    assert campos["Contact"].startswith("https://")
    assert sum(linha.startswith("Expires:") for linha in linhas) == 1


@override_settings(MODO_DEMONSTRACAO=True, URL_PUBLICA="")
def test_security_txt_sem_url_publica_nao_tem_canonical(client: Client) -> None:
    linhas = _linhas(client, "/.well-known/security.txt")

    assert not any(linha.startswith("Canonical:") for linha in linhas)
    assert any(linha.startswith("Contact:") for linha in linhas)


@pytest.mark.django_db
@override_settings(MODO_DEMONSTRACAO=False, URL_PUBLICA=URL_PUBLICA_TESTE)
def test_security_txt_sem_o_modo_responde_404(client: Client) -> None:
    resposta = client.get("/.well-known/security.txt", HTTP_HOST=HOST_DO_PEDIDO)

    assert resposta.status_code == 404


def test_expires_do_security_txt_ainda_vale() -> None:
    """
    ADR-6: falha 30 dias antes do vencimento, para dar tempo de rever o contato.

    Ao falhar, confira se o contato e a política continuam valendo e mova a
    data de EXPIRACAO_SECURITY_TXT (blog_culinario/descoberta.py) para até um
    ano à frente, como recomenda a RFC 9116.
    """
    expira = datetime.fromisoformat(EXPIRACAO_SECURITY_TXT)
    restante = expira - timezone.now()

    assert restante > timedelta(days=30), "security.txt vence em menos de 30 dias"
    assert restante <= timedelta(days=366), "Expires a mais de um ano (RFC 9116)"


# ---------------------------------------------------------------------------
# Métodos aceitos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(MODO_DEMONSTRACAO=True, URL_PUBLICA=URL_PUBLICA_TESTE)
@pytest.mark.parametrize(
    "caminho", ["/robots.txt", "/sitemap.xml", "/.well-known/security.txt"]
)
def test_arquivos_de_descoberta_so_respondem_get(client: Client, caminho: str) -> None:
    resposta = client.post(caminho, HTTP_HOST=HOST_DO_PEDIDO)

    assert resposta.status_code == 405


@pytest.mark.django_db
@override_settings(MODO_DEMONSTRACAO=True, URL_PUBLICA=URL_PUBLICA_TESTE)
@pytest.mark.parametrize(
    "caminho", ["/robots.txt", "/sitemap.xml", "/.well-known/security.txt"]
)
def test_arquivos_de_descoberta_aceitam_head(client: Client, caminho: str) -> None:
    """Desvio 1: robôs conferem o arquivo com HEAD antes do GET."""
    resposta = client.head(caminho, HTTP_HOST=HOST_DO_PEDIDO)

    assert resposta.status_code == 200
