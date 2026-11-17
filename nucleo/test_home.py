"""
Testes da home redesenhada (spec 012, RF-01 a RF-11, RNF-02).

Estratégia de isolamento: ORM e cliente HTTP de teste do Django, contra o banco
de teste do pytest-django, sem mock. O HTML é conferido pelo texto e pelos
atributos renderizados, como nos testes de interface da spec 008. Os caminhos
citados no "Por dentro" são conferidos contra os arquivos do próprio
repositório (RF-10).
"""

from __future__ import annotations

import re
from datetime import timedelta
from html.parser import HTMLParser
from itertools import pairwise
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest_django import DjangoAssertNumQueries

from blog_culinario.demonstracao import URL_REPOSITORIO
from receitas.models import Categoria, Comentario, Receita

pytestmark = pytest.mark.django_db

User = get_user_model()

# Raiz do repositório: os caminhos citados no "Por dentro" partem dela (RF-10).
RAIZ = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------
def _categoria(nome: str = "Sobremesas") -> Categoria:
    """
    Cria uma categoria.

    Args:
        nome (str, optional): nome da categoria. Padrão: ``"Sobremesas"``.

    Returns:
        Categoria: instância já persistida.
    """
    return Categoria.objects.create(nome=nome)


def _receita(**kwargs: Any) -> Receita:
    """
    Cria uma receita publicada mínima, sobrescrevível por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default (``titulo``,
            ``categoria``, ``publicado``, etc.).

    Returns:
        Receita: instância já persistida.
    """
    dados: dict[str, Any] = {
        "titulo": f"Receita {uuid4().hex[:6]}",
        "resumo": "Resumo de teste.",
        "ingredientes": "1 ingrediente",
        "modo_de_preparo": "Misture tudo.",
        "tempo_preparo_minutos": 30,
        "porcoes": 4,
        "categoria": kwargs.pop("categoria", None) or _categoria(),
        "publicado": True,
    }
    dados.update(kwargs)
    return Receita.objects.create(**dados)


def _comentario(receita: Receita, aprovado: bool = True) -> Comentario:
    """
    Cria um comentário numa receita, com um autor novo.

    Args:
        receita (Receita): receita comentada.
        aprovado (bool, optional): se o comentário está aprovado. Padrão: ``True``.

    Returns:
        Comentario: instância já persistida.
    """
    autor = User.objects.create_user(
        username=f"leitor-{uuid4().hex[:8]}", password="senha-forte-123"
    )
    return Comentario.objects.create(
        receita=receita, autor=autor, texto="Ficou ótimo.", aprovado=aprovado
    )


def _home(client: Client) -> Any:
    """
    Abre a home.

    Args:
        client (Client): cliente HTTP de teste.

    Returns:
        Any: a resposta, com ``context`` e ``content``.
    """
    return client.get(reverse("nucleo:home"))


# -----------------------------------------------------------------------------
# Contexto da view (RF-03, RF-05, RF-07, ADR-1)
# -----------------------------------------------------------------------------
def test_destaque_e_a_mais_recente_e_as_recentes_nao_a_repetem(client: Client) -> None:
    receitas = [_receita(titulo=f"Receita {n}") for n in range(5)]
    # Criadas no mesmo instante, empatariam no criado_em (o relógio do Windows
    # tem resolução grossa); um minuto entre cada uma fixa a ordem.
    agora = timezone.now()
    for minutos, receita in enumerate(receitas):
        Receita.objects.filter(pk=receita.pk).update(
            criado_em=agora + timedelta(minutes=minutos)
        )

    contexto = _home(client).context

    # ordering = ["-criado_em"]: a última criada é a mais recente.
    assert contexto["destaque"] == receitas[4]
    assert contexto["recentes"] == [receitas[3], receitas[2], receitas[1]]


def test_rascunho_nao_entra_no_destaque_nem_nas_contagens(client: Client) -> None:
    publicada = _receita()
    rascunho = _receita(publicado=False)
    _comentario(rascunho)

    contexto = _home(client).context

    assert contexto["destaque"] == publicada
    assert contexto["total_receitas"] == 1
    assert contexto["total_comentarios"] == 0


def test_conta_so_comentarios_aprovados(client: Client) -> None:
    receita = _receita()
    _comentario(receita)
    _comentario(receita, aprovado=False)

    assert _home(client).context["total_comentarios"] == 1


def test_sem_receita_publicada_nao_ha_destaque(client: Client) -> None:
    contexto = _home(client).context

    assert contexto["destaque"] is None
    assert contexto["recentes"] == []
    assert contexto["categorias"] == []


# -----------------------------------------------------------------------------
# Consultas fixas (RNF-02)
# -----------------------------------------------------------------------------
def test_numero_de_consultas_nao_cresce_com_as_receitas(
    client: Client, django_assert_num_queries: DjangoAssertNumQueries
) -> None:
    """Uma receita ou doze, em várias categorias: a home faz as mesmas consultas."""
    _comentario(_receita())
    with CaptureQueriesContext(connection) as com_uma:
        _home(client)

    for indice in range(11):
        _comentario(_receita(categoria=_categoria(nome=f"Categoria {indice % 5}")))
    with django_assert_num_queries(len(com_uma.captured_queries)):
        _home(client)


# -----------------------------------------------------------------------------
# Leitura do HTML
# -----------------------------------------------------------------------------
class _Leitor(HTMLParser):
    """
    Junta os níveis de título e os links de uma página renderizada.

    Attributes:
        niveis (list[int]): nível de cada ``h1``-``h6``, na ordem da página.
        links (list[dict[str, str | None]]): atributos de cada ``<a>``.
    """

    def __init__(self) -> None:
        """Começa sem nenhum título nem link lido."""
        super().__init__()
        self.niveis: list[int] = []
        self.links: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Registra títulos e links.

        Args:
            tag (str): nome da tag aberta.
            attrs (list[tuple[str, str | None]]): atributos da tag.

        Returns:
            None
        """
        if re.fullmatch(r"h[1-6]", tag):
            self.niveis.append(int(tag[1]))
        elif tag == "a":
            self.links.append(dict(attrs))


def _ler(html: str) -> _Leitor:
    """
    Lê títulos e links de uma página.

    Args:
        html (str): HTML renderizado.

    Returns:
        _Leitor: o leitor com ``niveis`` e ``links`` preenchidos.
    """
    leitor = _Leitor()
    leitor.feed(html)
    return leitor


def _trecho(html: str, inicio: str, fim: str) -> str:
    """
    Recorta o HTML entre dois marcadores.

    Args:
        html (str): HTML renderizado.
        inicio (str): texto que abre o trecho.
        fim (str): texto que fecha o trecho, procurado depois do início.

    Returns:
        str: o trecho, do início ao fim (exclusive).
    """
    comeco = html.index(inicio)
    return html[comeco : html.index(fim, comeco)]


def _html(client: Client) -> str:
    """
    HTML da home.

    Args:
        client (Client): cliente HTTP de teste.

    Returns:
        str: o corpo da resposta.
    """
    return str(_home(client).content.decode())


# -----------------------------------------------------------------------------
# Abertura (RF-01 a RF-04)
# -----------------------------------------------------------------------------
def test_abertura_tem_duas_colunas_com_receita_e_uma_sem(client: Client) -> None:
    vazia = _html(client)
    _receita()
    com_receita = _html(client)

    assert "hero-dividido--uma-coluna" in vazia
    assert "hero-dividido--uma-coluna" not in com_receita
    assert "Receitas simples para todos os dias." in com_receita


def test_busca_da_abertura_leva_a_listagem(client: Client) -> None:
    formulario = _trecho(_html(client), '<form class="busca-hero"', "</form>")

    assert 'method="get"' in formulario
    assert f'action="{reverse("receitas:lista")}"' in formulario
    assert 'role="search"' in formulario
    rotulo = '<label for="busca-home">Buscar por título ou ingrediente</label>'
    assert rotulo in formulario
    assert 'id="busca-home" name="q"' in formulario
    assert 'placeholder="Ex.: cenoura"' in formulario
    assert ">Buscar</button>" in formulario


def test_numeros_no_plural(client: Client) -> None:
    for nome in ("Massas", "Lanches"):
        _comentario(_receita(categoria=_categoria(nome)))

    numeros = _trecho(_html(client), '<ul class="numeros"', "</ul>")

    assert "<strong>2</strong> receitas" in numeros
    assert "<strong>2</strong> categorias" in numeros
    assert "<strong>2</strong> comentários" in numeros


def test_numeros_no_singular_e_zero_some(client: Client) -> None:
    _receita()

    numeros = _trecho(_html(client), '<ul class="numeros"', "</ul>")

    assert "<strong>1</strong> receita<" in numeros
    assert "<strong>1</strong> categoria<" in numeros
    assert "comentário" not in numeros


def test_sem_nada_publicado_a_linha_de_numeros_some(client: Client) -> None:
    assert 'class="numeros"' not in _html(client)


def test_convite_a_conta_so_sem_login(client: Client) -> None:
    anonimo = _html(client)
    client.force_login(User.objects.create_user("bia", password="senha-forte-123"))
    logado = _html(client)

    assert "Quer comentar uma receita?" in anonimo
    assert f'href="{reverse("usuarios:cadastro")}">Crie sua conta.</a>' in anonimo
    assert "Quer comentar uma receita?" not in logado


# -----------------------------------------------------------------------------
# Receita em destaque (RF-05, RNF-05)
# -----------------------------------------------------------------------------
def test_destaque_tem_um_link_no_titulo_e_a_capa_fora_do_tab(client: Client) -> None:
    receita = _receita(titulo="Shakshuka", resumo="Ovos no molho de tomate.")

    destaque = _trecho(_html(client), '<article class="destaque"', "</article>")
    links = _ler(destaque).links

    assert "A receita mais nova" in destaque
    assert "Ovos no molho de tomate." in destaque
    assert len(links) == 2
    assert links[0]["aria-hidden"] == "true" and links[0]["tabindex"] == "-1"
    assert links[1]["href"] == reverse("receitas:detalhe", args=[receita.slug])
    assert '<h2 class="destaque__titulo"' in destaque


def test_capa_do_destaque_nao_e_lazy(client: Client) -> None:
    receita = _receita()
    Receita.objects.filter(pk=receita.pk).update(imagem_capa="receitas/capas/x.webp")

    destaque = _trecho(_html(client), '<article class="destaque"', "</article>")

    assert "<img" in destaque
    assert 'class="destaque__imagem"' in destaque
    assert 'loading="lazy"' not in destaque


# -----------------------------------------------------------------------------
# Categorias (RF-06)
# -----------------------------------------------------------------------------
def test_pilulas_com_contagem_ordem_e_link_de_filtro(client: Client) -> None:
    massas = _categoria("Massas")
    lanches = _categoria("Lanches")
    for _ in range(2):
        _receita(categoria=massas)
    _receita(categoria=lanches)
    _receita(categoria=_categoria("Rascunhos"), publicado=False)

    secao = _trecho(_html(client), 'aria-labelledby="titulo-categorias"', "</section>")

    assert "Comece pelo que tem vontade" in secao
    assert secao.index("Massas") < secao.index("Lanches")
    assert "2 receitas" in secao and "1 receita<" in secao
    assert f'href="{reverse("receitas:lista")}?categoria={massas.slug}"' in secao
    assert "Rascunhos" not in secao


def test_sem_categoria_com_receita_a_secao_some(client: Client) -> None:
    _receita(publicado=False)

    assert "titulo-categorias" not in _html(client)


# -----------------------------------------------------------------------------
# Recentes (RF-07)
# -----------------------------------------------------------------------------
def test_recentes_mostram_tres_e_o_botao_com_o_total(client: Client) -> None:
    for indice in range(6):
        _receita(titulo=f"Prato {indice}")

    secao = _trecho(_html(client), 'id="receitas-recentes"', "</section>")

    assert secao.count('<article class="cartao-receita">') == 3
    assert "Recém-saídas do forno" in secao
    assert "Ver todas as 6 receitas" in secao


def test_com_uma_receita_a_secao_de_recentes_some(client: Client) -> None:
    _receita()

    assert 'id="receitas-recentes"' not in _html(client)


def test_sem_receita_publicada_mostra_o_estado_vazio(client: Client) -> None:
    secao = _trecho(_html(client), 'id="receitas-recentes"', "</section>")

    assert "Nenhuma receita publicada ainda." in secao


# -----------------------------------------------------------------------------
# Por dentro (RF-09, RF-10)
# -----------------------------------------------------------------------------
def test_por_dentro_tem_as_quatro_notas_com_link_para_o_codigo(client: Client) -> None:
    secao = _trecho(_html(client), 'id="por-dentro"', "</section>")
    links = [link["href"] or "" for link in _ler(secao).links]

    titulos = ("Esta página", "Busca e filtros", "Segurança", "Specs antes do código")
    for titulo in titulos:
        assert f"<h3>{titulo}</h3>" in secao
    assert f"{URL_REPOSITORIO}/blob/main/nucleo/views.py" in links
    assert f"{URL_REPOSITORIO}/tree/main/specs" in links
    assert "Ver o projeto no GitHub" in secao


def test_cada_caminho_citado_no_por_dentro_existe(client: Client) -> None:
    """RF-10: mover ou renomear o arquivo sem atualizar a nota quebra este teste."""
    secao = _trecho(_html(client), 'id="por-dentro"', "</section>")
    prefixo = f"{URL_REPOSITORIO}/"
    caminhos = [
        re.sub(r"^(blob|tree)/main/", "", link["href"][len(prefixo) :])
        for link in _ler(secao).links
        if link["href"] and link["href"].startswith(prefixo)
    ]

    assert len(caminhos) == 4
    for caminho in caminhos:
        assert (RAIZ / caminho).exists(), caminho


def test_a_nota_esta_pagina_descreve_o_codigo_de_verdade() -> None:
    """RF-10: a view usa select_related e a contagem vem de um annotate(Count)."""
    view = (RAIZ / "nucleo/views.py").read_text(encoding="utf-8")
    modelos = (RAIZ / "receitas/models.py").read_text(encoding="utf-8")

    assert 'select_related("categoria")' in view
    assert "com_receitas_publicadas()" in view
    assert "annotate(" in modelos and "Count(" in modelos


# -----------------------------------------------------------------------------
# Rótulos e títulos (RF-11, RNF-04)
# -----------------------------------------------------------------------------
def test_rotulos_ficam_fora_do_titulo(client: Client) -> None:
    for _ in range(2):
        _receita()
    html = _html(client)

    for rotulo in (
        "Por categoria",
        "Recém-saídas do forno",
        "Por dentro",
        "A receita mais nova",
    ):
        assert f'<span class="rotulo">{rotulo}</span>' in html
        assert not re.search(rf"<h2[^>]*>[^<]*{rotulo}", html)


def test_titulos_da_home_nao_pulam_nivel(client: Client) -> None:
    for _ in range(4):
        _receita()

    niveis = _ler(_html(client)).niveis

    assert niveis.count(1) == 1 and niveis[0] == 1
    for anterior, atual in pairwise(niveis):
        assert atual <= anterior + 1, niveis
