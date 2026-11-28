"""
Testes do rodapé em colunas e do menu do celular (spec 012, RF-12 a RF-17).

Estratégia de isolamento: ORM e cliente HTTP de teste do Django, sem mock. O
rodapé e o menu são conferidos na listagem de receitas, uma página comum que
estende o ``base.html``; o CSS e o JavaScript são lidos do arquivo, como nos
testes de interface da spec 008 (não há navegador no pytest).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from blog_culinario.demonstracao import URL_REPOSITORIO
from receitas.models import Categoria, Receita

pytestmark = pytest.mark.django_db

User = get_user_model()

RAIZ = Path(__file__).resolve().parent.parent
CSS_BASE = (RAIZ / "static/css/base.css").read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Apoio
# -----------------------------------------------------------------------------
def _receita(categoria: Categoria, publicado: bool = True) -> Receita:
    """
    Cria uma receita mínima numa categoria.

    Args:
        categoria (Categoria): categoria da receita.
        publicado (bool, optional): se a receita está publicada. Padrão: ``True``.

    Returns:
        Receita: instância já persistida.
    """
    return Receita.objects.create(
        titulo=f"Receita de {categoria.nome}",
        resumo="Resumo de teste.",
        ingredientes="1 ingrediente",
        modo_de_preparo="Misture tudo.",
        tempo_preparo_minutos=10,
        porcoes=2,
        categoria=categoria,
        publicado=publicado,
    )


def _rodape(client: Client) -> str:
    """
    O rodapé da listagem de receitas.

    Args:
        client (Client): cliente HTTP de teste.

    Returns:
        str: o HTML do ``<footer>`` ao ``</footer>``.
    """
    html = client.get(reverse("receitas:lista")).content.decode()
    return html[html.index('<footer class="rodape">') : html.index("</footer>")]


def _bloco_css(seletor: str) -> str:
    """
    Corpo da primeira regra do ``base.css`` cujo seletor abre uma linha.

    Args:
        seletor (str): seletor exato, como ``".rodape__base"``.

    Returns:
        str: texto entre as chaves da regra.
    """
    achado = re.search(
        rf"(?m)^{re.escape(seletor)}\s*\{{(.*?)^\}}", CSS_BASE, flags=re.DOTALL
    )
    assert achado, f"regra {seletor!r} não encontrada"
    return achado.group(1)


# -----------------------------------------------------------------------------
# Rodapé em colunas (RF-12)
# -----------------------------------------------------------------------------
def test_rodape_tem_as_colunas_com_regioes_de_navegacao(client: Client) -> None:
    _receita(Categoria.objects.create(nome="Massas"))

    rodape = _rodape(client)

    assert '<p class="rodape__marca">Blog Culinário</p>' in rodape
    for ancora, titulo in (
        ("rodape-navegar", "Navegar"),
        ("rodape-categorias", "Categorias"),
        ("rodape-projeto", "O projeto"),
    ):
        assert f'aria-labelledby="{ancora}"' in rodape
        assert f'id="{ancora}">{titulo}</h2>' in rodape


def test_rodape_aponta_os_documentos_do_projeto(client: Client) -> None:
    rodape = _rodape(client)

    assert f'href="{URL_REPOSITORIO}"' in rodape
    for caminho, texto in (
        ("docs/stack.md", "Mapa da stack"),
        ("SECURITY.md", "Política de segurança"),
        ("LICENSE", "Licença MIT"),
    ):
        assert f'href="{URL_REPOSITORIO}/blob/main/{caminho}"' in rodape
        assert texto in rodape
        assert (RAIZ / caminho).is_file()


def test_rodape_lista_as_categorias_publicadas_na_ordem_da_home(
    client: Client,
) -> None:
    lanches = Categoria.objects.create(nome="Lanches")
    massas = Categoria.objects.create(nome="Massas")
    _receita(massas)
    _receita(massas)
    _receita(lanches)
    _receita(Categoria.objects.create(nome="Rascunhos"), publicado=False)

    rodape = _rodape(client)

    assert rodape.index(">Massas<") < rodape.index(">Lanches<")
    assert f'?categoria={massas.slug}"' in rodape
    assert "Rascunhos" not in rodape


def test_sem_categoria_publicada_a_coluna_some(client: Client) -> None:
    assert "rodape-categorias" not in _rodape(client)


def test_entrar_e_cadastrar_no_rodape_so_sem_login(client: Client) -> None:
    anonimo = _rodape(client)
    client.force_login(User.objects.create_user("caio", password="senha-forte-123"))
    logado = _rodape(client)

    assert reverse("usuarios:entrar") in anonimo
    assert reverse("usuarios:cadastro") in anonimo
    assert reverse("usuarios:entrar") not in logado
    assert reverse("usuarios:cadastro") not in logado


def test_copyright_centrado_abaixo_das_colunas(client: Client) -> None:
    rodape = _rodape(client)
    base = _bloco_css(".rodape__base")

    assert re.search(r'<p class="rodape__base">&copy; \d{4} Blog Culinário</p>', rodape)
    assert "text-align: center;" in base
    assert "border-top:" in base


# -----------------------------------------------------------------------------
# Páginas de erro (RF-13)
# -----------------------------------------------------------------------------
def test_paginas_de_erro_ficam_com_o_rodape_de_uma_linha() -> None:
    """O rodapé de uma linha não chama a tag das categorias nem lê a sessão."""
    # Com uma categoria publicada, a tag das categorias desenharia a coluna: sem
    # ela, a coluna some de qualquer jeito, e o teste não teria como falhar.
    _receita(Categoria.objects.create(nome="Massas"))
    assert "rodape-categorias" in _rodape(Client())

    for template in ("400.html", "403.html", "403_csrf.html", "404.html", "500.html"):
        html = render_to_string(template)
        assert 'class="rodape rodape--linha"' in html
        assert "rodape-categorias" not in html
        assert "Massas" not in html


# -----------------------------------------------------------------------------
# Menu do celular (RF-14 a RF-17)
# -----------------------------------------------------------------------------
def _barra(client: Client, rota: str = "receitas:lista") -> str:
    """
    A barra do site numa página.

    Args:
        client (Client): cliente HTTP de teste.
        rota (str, optional): nome da rota aberta. Padrão: ``"receitas:lista"``.

    Returns:
        str: o HTML do ``<header class="navbar">`` ao ``</header>``.
    """
    html = client.get(reverse(rota)).content.decode()
    return html[html.index('<header class="navbar">') : html.index("</header>")]


def test_botao_do_menu_tem_nome_estado_e_os_dois_icones(client: Client) -> None:
    barra = _barra(client)
    botao = barra[barra.index("<button") : barra.index("</button>")]

    assert 'aria-controls="menu-principal"' in botao
    assert 'aria-expanded="false"' in botao
    assert 'aria-label="Abrir menu de navegação"' in botao
    assert "navbar__icone--menu" in botao and "navbar__icone--fechar" in botao
    assert botao.count('aria-hidden="true"') == 2
    assert 'id="menu-principal"' in barra


def test_link_da_pagina_atual_fica_marcado(client: Client) -> None:
    home = _barra(client, "nucleo:home")
    lista = _barra(client, "receitas:lista")

    assert f'href="{reverse("nucleo:home")}" aria-current="page"' in home
    assert f'href="{reverse("receitas:lista")}" aria-current="page"' not in home
    assert f'href="{reverse("receitas:lista")}" aria-current="page"' in lista
    # O par: na listagem, o "Início" não fica marcado (uma página atual só).
    assert f'href="{reverse("nucleo:home")}" aria-current="page"' not in lista


def test_grupo_sua_conta_sem_login(client: Client) -> None:
    conta = _barra(client).split('class="navbar__conta"')[1]

    assert "Sua conta" in conta
    assert f'class="navbar__acao" href="{reverse("usuarios:entrar")}"' in conta
    assert "navbar__acao navbar__acao--principal" in conta
    assert "Sair" not in conta


def test_grupo_sua_conta_com_login(client: Client) -> None:
    client.force_login(User.objects.create_user("davi", password="senha-forte-123"))

    conta = _barra(client).split('class="navbar__conta"')[1]

    assert "Olá, davi" in conta
    assert f'action="{reverse("usuarios:sair")}"' in conta
    assert reverse("usuarios:entrar") not in conta


def test_veu_comeca_escondido(client: Client) -> None:
    assert '<div class="navbar__veu" hidden></div>' in _barra(client)


def test_js_cuida_do_veu_do_inert_e_da_largura() -> None:
    js = (RAIZ / "static/js/interacoes.js").read_text(encoding="utf-8")

    assert "veu.hidden = false;" in js and "veu.hidden = true;" in js
    assert "elemento.inert = true;" in js and "elemento.inert = false;" in js
    assert 'classList.add("menu-aberto")' in js
    assert 'veu.addEventListener("click"' in js
    assert 'evento.target.closest("a")' in js
    assert 'const CONSULTA_CELULAR = "(max-width: 720px)";' in js


def test_painel_desliza_por_transform_e_para_com_movimento_reduzido() -> None:
    reduzido = CSS_BASE[CSS_BASE.index("@media (prefers-reduced-motion: reduce)") :]

    assert "transform: translateX(100%);" in CSS_BASE
    assert "transition: transform var(--transicao-padrao)" in CSS_BASE
    assert ".navbar__painel," in reduzido and ".navbar__painel--aberto" in reduzido
    assert 'aria-expanded="true"] .navbar__icone--fechar' in CSS_BASE
