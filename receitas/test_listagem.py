"""
Testes da listagem redesenhada (spec 012, adendo, RF-25 a RF-27).

Estratégia de isolamento: ``Client`` de teste do Django com os builders de
``receitas/tests.py``; o HTML é conferido por recortes, e as consultas por
``CaptureQueriesContext``.
"""

from __future__ import annotations

import re

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Receita
from .tests import _categoria, _receita, _tag

pytestmark = pytest.mark.django_db


def _listagem(client: Client, consulta: str = "") -> str:
    """
    Abre a listagem, com a querystring dada, e devolve o HTML.

    Args:
        client (Client): cliente de teste.
        consulta (str): querystring sem o ``?`` (``"q=bolo&categoria=doces"``).

    Returns:
        str: o HTML da resposta.
    """
    url = reverse("receitas:lista") + (f"?{consulta}" if consulta else "")
    resposta = client.get(url)
    assert resposta.status_code == 200
    return str(resposta.content.decode())


def _pilulas(html: str) -> list[tuple[str, str, bool]]:
    """
    Lê as pílulas de categoria da listagem.

    Args:
        html (str): o HTML da listagem.

    Returns:
        list[tuple[str, str, bool]]: para cada pílula, o texto sem espaços
        repetidos (``"Doces · 2"``), o ``href`` e se está marcada como atual.
    """
    regiao_nav = '<nav class="lista-categorias" aria-label="Filtrar por categoria">'
    inicio = html.index(regiao_nav)
    regiao = html[inicio : html.index("</nav>", inicio)]
    pilulas = []
    for atributos, corpo in re.findall(
        r'<a class="pilula" ([^>]*)>(.*?)</a>', regiao, re.S
    ):
        href = re.search(r'href="([^"]*)"', atributos)
        assert href
        # O texto visível: o " receitas" só do leitor de tela tem teste próprio.
        visivel = re.sub(r'<span class="so-leitor-de-tela">.*?</span>', "", corpo)
        texto = " ".join(re.sub(r"<[^>]+>", "", visivel).split())
        pilulas.append((texto, href.group(1), 'aria-current="page"' in atributos))
    return pilulas


def _tres_categorias() -> None:
    """Doces com 2 publicadas, Salgados com 1 e Massas só com rascunho."""
    doces = _categoria(nome="Doces")
    salgados = _categoria(nome="Salgados")
    massas = _categoria(nome="Massas")
    _receita(titulo="Pudim", categoria=doces, publicado=True)
    _receita(titulo="Bolo de cenoura", categoria=doces, publicado=True)
    _receita(titulo="Coxinha", categoria=salgados, publicado=True)
    _receita(titulo="Lasanha", categoria=massas, publicado=False)


# -----------------------------------------------------------------------------
# RF-25 — busca
# -----------------------------------------------------------------------------
def test_busca_tem_o_desenho_da_home(client: Client) -> None:
    """Rótulo, campo ``q`` e botão na linha da busca da home (RF-25)."""
    html = _listagem(client)
    busca = html[html.index('<form class="busca-hero"') : html.index("</form>")]
    assert 'method="get" role="search"' in busca
    assert '<label for="campo-busca">Buscar por título ou ingrediente</label>' in busca
    assert '<div class="busca-hero__linha">' in busca
    assert 'name="q"' in busca and 'placeholder="Ex.: cenoura"' in busca
    assert "formulario-busca" not in html


def test_busca_mantem_a_categoria_e_a_tag_ativas(client: Client) -> None:
    """Os ocultos levam o filtro ativo junto da busca (spec 003, RF-07)."""
    html = _listagem(client, "categoria=doces&tag=vegana")
    busca = html[html.index('<form class="busca-hero"') : html.index("</form>")]
    assert '<input type="hidden" name="categoria" value="doces" />' in busca
    assert '<input type="hidden" name="tag" value="vegana" />' in busca


# -----------------------------------------------------------------------------
# RF-26 — pílulas
# -----------------------------------------------------------------------------
def test_pilulas_na_ordem_da_home_com_todas_na_frente(client: Client) -> None:
    """A pílula "Todas" vem primeiro; depois por contagem, sem a de rascunho (RF-26)."""
    _tres_categorias()
    textos = [texto for texto, _, _ in _pilulas(_listagem(client))]
    assert textos == ["Todas · 3", "Doces · 2", "Salgados · 1"]


def test_sem_filtro_a_marcada_e_todas(client: Client) -> None:
    """Sem categoria na URL, "Todas" leva o ``aria-current`` (RF-26)."""
    _tres_categorias()
    marcadas = [texto for texto, _, atual in _pilulas(_listagem(client)) if atual]
    assert marcadas == ["Todas · 3"]


def test_com_categoria_a_marcada_e_ela(client: Client) -> None:
    """Filtrada por categoria, só a pílula dela fica marcada (RF-26)."""
    _tres_categorias()
    marcadas = [
        texto
        for texto, _, atual in _pilulas(_listagem(client, "categoria=doces"))
        if atual
    ]
    assert marcadas == ["Doces · 2"]


def test_contagens_ignoram_a_busca(client: Client) -> None:
    """Com uma busca ativa, os números continuam os de publicadas (RF-26)."""
    _tres_categorias()
    textos = [texto for texto, _, _ in _pilulas(_listagem(client, "q=coxinha"))]
    assert textos == ["Todas · 3", "Doces · 2", "Salgados · 1"]


def test_pilula_mantem_busca_e_tag_e_volta_a_primeira_pagina(client: Client) -> None:
    """O link troca a categoria, mantém ``q`` e ``tag`` e tira ``page`` (RF-26)."""
    _tres_categorias()
    pilulas = _pilulas(_listagem(client, "q=bolo&tag=vegana&categoria=salgados&page=1"))
    hrefs = {texto: href for texto, href, _ in pilulas}
    lista = reverse("receitas:lista")
    assert hrefs["Todas · 3"] == f"{lista}?q=bolo&amp;tag=vegana"
    assert hrefs["Doces · 2"] == f"{lista}?q=bolo&amp;tag=vegana&amp;categoria=doces"
    assert all("page=" not in href for href in hrefs.values())


def test_pilula_sem_outros_filtros_leva_so_a_categoria(client: Client) -> None:
    """Sem busca nem tag, o link é só ``?categoria=<slug>`` (RF-26)."""
    _tres_categorias()
    hrefs = {texto: href for texto, href, _ in _pilulas(_listagem(client))}
    lista = reverse("receitas:lista")
    assert hrefs["Todas · 3"] == lista
    assert hrefs["Doces · 2"] == f"{lista}?categoria=doces"


def test_sem_categoria_publicada_as_pilulas_somem(client: Client) -> None:
    """Sem receita publicada, não há região de categorias (RF-26)."""
    _receita(titulo="Só rascunho", publicado=False)
    assert "lista-categorias" not in _listagem(client)


def test_contagem_diz_receitas_ao_leitor_de_tela(client: Client) -> None:
    """Sem a palavra, o leitor de tela lia "Doces 2", como parte do nome."""
    _tres_categorias()

    html = client.get(reverse("receitas:lista")).content.decode()

    assert '3<span class="so-leitor-de-tela">&nbsp;receitas</span>' in html
    assert '2<span class="so-leitor-de-tela">&nbsp;receitas</span>' in html
    assert '1<span class="so-leitor-de-tela">&nbsp;receita</span>' in html


def test_total_de_todas_bate_com_a_contagem_do_banco(client: Client) -> None:
    """A soma das categorias é o total de publicadas (ADR-11)."""
    _tres_categorias()
    resposta = client.get(reverse("receitas:lista"))
    total = Receita.objects.filter(publicado=True).count()
    assert resposta.context["total_publicadas"] == total == 3


# -----------------------------------------------------------------------------
# RF-27 e RNF-08 — paginação e consultas
# -----------------------------------------------------------------------------
def test_paginacao_continua_com_9_por_pagina(client: Client) -> None:
    """Com 10 publicadas, a primeira página tem 9 e a segunda, 1 (RF-27)."""
    categoria = _categoria(nome="Doces")
    for i in range(10):
        _receita(titulo=f"Receita {i}", categoria=categoria, publicado=True)
    primeira = client.get(reverse("receitas:lista"))
    segunda = client.get(reverse("receitas:lista") + "?page=2")
    assert len(primeira.context["receitas"]) == 9
    assert len(segunda.context["receitas"]) == 1


def test_consultas_da_listagem_nao_crescem_com_o_blog(client: Client) -> None:
    """O número de consultas é o mesmo com 2 e com 12 receitas (RNF-08)."""
    for i in range(2):
        receita = _receita(
            titulo=f"Receita {i}",
            categoria=_categoria(nome=f"Categoria {i}"),
            publicado=True,
        )
        receita.tags.add(_tag(nome=f"tag-{i}"))
    with CaptureQueriesContext(connection) as poucas:
        client.get(reverse("receitas:lista"))
    for i in range(2, 12):
        receita = _receita(
            titulo=f"Receita {i}",
            categoria=_categoria(nome=f"Categoria {i}"),
            publicado=True,
        )
        receita.tags.add(_tag(nome=f"tag-{i}"))
    with CaptureQueriesContext(connection) as muitas:
        client.get(reverse("receitas:lista"))
    assert len(muitas) == len(poucas)
