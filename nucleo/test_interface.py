"""
Testes das correções da auditoria de interface (spec 008).

Cada teste guarda uma correção: se ela for desfeita, o teste falha. Os de
marcação renderizam as páginas pelo client do Django; os de CSS e JavaScript leem
o arquivo estático (não há navegador no pytest) e conferem a regra que o
navegador aplica. A medição em Chrome real (axe, Tab, CLS, proporção dos botões)
fica registrada em ``specs/008-correcoes-de-interface/tasks.md``.

Estratégia de isolamento: ORM e HTTP de teste do Django, sem mock.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from django.urls import reverse
from django.views.defaults import permission_denied, server_error

from receitas.models import Categoria, Receita, Tag

pytestmark = pytest.mark.django_db

RAIZ = Path(__file__).resolve().parent.parent
CSS_BASE = (RAIZ / "static/css/base.css").read_text(encoding="utf-8")
CSS_TOKENS = (RAIZ / "static/css/tokens.css").read_text(encoding="utf-8")
CSS_FONTES = (RAIZ / "static/css/fontes.css").read_text(encoding="utf-8")
JS_INTERACOES = (RAIZ / "static/js/interacoes.js").read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Apoio
# -----------------------------------------------------------------------------
def _receita_publicada(
    titulo: str = "Bolo de cenoura", categoria: Categoria | None = None
) -> Receita:
    """
    Cria uma receita publicada mínima.

    Args:
        titulo (str, optional): título da receita. Padrão: ``"Bolo de cenoura"``.
        categoria (Categoria | None, optional): categoria já existente; sem ela,
            cria a categoria "Sobremesas". Padrão: ``None``.

    Returns:
        Receita: instância persistida, com ``publicado=True``.
    """
    categoria = categoria or Categoria.objects.create(nome="Sobremesas")
    return Receita.objects.create(
        titulo=titulo,
        resumo="Resumo de teste.",
        ingredientes="1 ingrediente",
        modo_de_preparo="Misture tudo.",
        tempo_preparo_minutos=10,
        porcoes=1,
        categoria=categoria,
        publicado=True,
    )


def _bloco_css(css: str, seletor: str) -> str:
    """
    Devolve o corpo da primeira regra cujo seletor abre uma linha.

    Args:
        css (str): texto da folha de estilo.
        seletor (str): seletor exato, como ``".botao"`` ou ``":root"``.

    Returns:
        str: texto entre as chaves da regra.

    Raises:
        AssertionError: se a regra não existe na folha.
    """
    achado = re.search(
        rf"(?m)^{re.escape(seletor)}\s*\{{(.*?)^\}}", css, flags=re.DOTALL
    )
    assert achado, f"regra {seletor!r} não encontrada"
    return achado.group(1)


def _token(css: str, nome: str) -> str:
    """
    Lê o valor de uma custom property do primeiro ``:root``.

    Args:
        css (str): texto de ``tokens.css``.
        nome (str): nome da variável, como ``"--cor-borda-campo"``.

    Returns:
        str: valor declarado, sem espaços nas pontas.
    """
    achado = re.search(rf"{re.escape(nome)}:\s*([^;]+);", css)
    assert achado, f"token {nome!r} não encontrado"
    return achado.group(1).strip()


def _luminancia(cor: str) -> float:
    """
    Luminância relativa (WCAG) de uma cor ``#rrggbb``.

    Args:
        cor (str): cor hexadecimal de 6 dígitos.

    Returns:
        float: luminância de 0 (preto) a 1 (branco).
    """

    def canal(valor: int) -> float:
        c = valor / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(cor[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def _contraste(cor_a: str, cor_b: str) -> float:
    """
    Razão de contraste WCAG entre duas cores ``#rrggbb``.

    Args:
        cor_a (str): primeira cor.
        cor_b (str): segunda cor.

    Returns:
        float: razão de 1 a 21.
    """
    mais_clara, mais_escura = sorted(
        (_luminancia(cor_a), _luminancia(cor_b)), reverse=True
    )
    return (mais_clara + 0.05) / (mais_escura + 0.05)


class _Ids(HTMLParser):
    """Coleta os ``id`` e os ``aria-describedby`` de uma página."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.descritos: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Guarda ``id`` e referências de ``aria-describedby`` da tag aberta.

        Args:
            tag (str): nome da tag.
            attrs (list[tuple[str, str | None]]): atributos da tag.
        """
        for nome, valor in attrs:
            if nome == "id" and valor:
                self.ids.add(valor)
            if nome == "aria-describedby" and valor:
                self.descritos.extend(valor.split())


# -----------------------------------------------------------------------------
# Botões, capa, movimento e campos: CSS (RF-08, RF-09, RF-10, RF-11, RF-16)
# -----------------------------------------------------------------------------
def test_botao_herda_a_fonte_e_centraliza_o_rotulo() -> None:
    """RF-10: fonte do corpo no <button> e rótulo no meio da caixa."""
    # Sem `font: inherit` o <button> sai em Arial 13 px; sem justify-content, o
    # rótulo de um botão de largura total fica colado à esquerda.
    botao = _bloco_css(CSS_BASE, ".botao")

    assert "font: inherit;" in botao
    assert "justify-content: center;" in botao
    assert "text-align: center;" in botao
    # O peso vem depois de `font: inherit`, que o zeraria se viesse antes.
    assert botao.index("font: inherit;") < botao.index("font-weight: 600;")


def test_botao_de_formulario_largo_no_celular_e_do_tamanho_do_texto_no_desktop() -> (
    None
):
    """RF-10, ADR-1: largura total só no celular; no desktop, o tamanho do rótulo."""
    assert "align-self: stretch;" in _bloco_css(CSS_BASE, ".formulario .botao")
    desktop = re.search(
        r"@media \(min-width: 721px\) \{(.*?)\n\}", CSS_BASE, flags=re.DOTALL
    )
    assert desktop, "bloco de formulário em tela larga ausente"
    assert "align-self: flex-start;" in desktop.group(1)
    assert "align-self: center;" in desktop.group(1)


def test_capa_da_receita_reserva_o_espaco_antes_da_foto() -> None:
    """RF-09: sem ``aspect-ratio`` a foto empurra o texto quando chega (CLS 0,226)."""
    assert "aspect-ratio: 4 / 3;" in _bloco_css(CSS_BASE, ".receita-detalhe__capa")


def test_movimento_reduzido_desliga_rolagem_suave_e_elevacao() -> None:
    """RF-11: quem pede menos movimento não recebe rolagem suave nem hover animado."""
    achado = re.search(
        r"@media \(prefers-reduced-motion: reduce\) \{(.*)\n\}", CSS_BASE, re.DOTALL
    )
    assert achado, "bloco prefers-reduced-motion ausente"
    bloco = achado.group(1)

    assert "scroll-behavior: auto;" in bloco
    assert "transition: none;" in bloco
    assert "transform: none;" in bloco


def test_borda_dos_campos_tem_contraste_de_3_para_1() -> None:
    """RF-08: borda de componente de interface pede 3:1 (WCAG 1.4.11)."""
    borda = _token(CSS_TOKENS, "--cor-borda-campo")

    assert _contraste(borda, _token(CSS_TOKENS, "--cor-superficie")) >= 3
    assert _contraste(borda, _token(CSS_TOKENS, "--cor-fundo")) >= 3


def test_campos_usam_o_token_de_borda_de_campo() -> None:
    """RF-08: os dois grupos de campo (busca e formulário) usam o token novo."""
    busca = _bloco_css(CSS_BASE, '.formulario-busca input[type="search"]')
    formulario = _bloco_css(
        CSS_BASE, ".formulario__campo input,\n.formulario__campo textarea"
    )

    assert "var(--cor-borda-campo)" in busca
    assert "var(--cor-borda-campo)" in formulario


def test_mensagem_de_erro_usa_token_e_nao_cor_crua() -> None:
    """RNF-02: o ``#f8d7da`` virou ``--cor-erro-fundo`` (o tema escuro precisa dele)."""
    assert "#f8d7da" not in CSS_BASE
    assert "var(--cor-erro-fundo)" in _bloco_css(CSS_BASE, ".mensagem--error")


def test_alvo_da_categoria_tem_pelo_menos_24_px_de_altura() -> None:
    """RF-16: o link da categoria tem alvo de 24 px ou mais (WCAG 2.5.8)."""
    # Altura = 0,8 rem x 1,65 de linha (21 px) + 2 x 0,25 rem de respiro (8 px);
    # antes eram 15 px.
    categoria = _bloco_css(CSS_BASE, ".cartao-receita__categoria")

    assert "display: inline-block;" in categoria
    assert "padding-block: var(--espaco-1);" in categoria


def test_estado_vazio_e_coluna_de_formulario_ficam_centrados() -> None:
    """RF-17, ADR-5: o que é curto e isolado fica no centro."""
    assert "text-align: center;" in _bloco_css(CSS_BASE, ".estado-vazio")
    coluna = _bloco_css(CSS_BASE, ".pagina-formulario")
    assert "text-align: center;" in coluna
    assert "max-width:" in coluna
    assert "margin-inline: auto;" in _bloco_css(
        CSS_BASE, ".pagina-formulario .formulario"
    )


# -----------------------------------------------------------------------------
# Cartões e lista (RF-02, RF-03, RF-13, RF-17)
# -----------------------------------------------------------------------------
def test_link_da_foto_do_cartao_fica_fora_do_tab_e_do_leitor_de_tela(
    client: Client,
) -> None:
    """RF-02: o link da foto repete o do título e sai do Tab e do leitor."""
    _receita_publicada()

    html = client.get(reverse("nucleo:home")).content.decode()
    cartao = html[html.index('<article class="cartao-receita">') :]
    primeiro_link = re.search(r"<a [^>]*>", cartao)

    assert primeiro_link
    assert 'aria-hidden="true"' in primeiro_link.group(0)
    assert 'tabindex="-1"' in primeiro_link.group(0)


def test_lista_tem_h2_oculto_entre_o_h1_e_os_cartoes(client: Client) -> None:
    """RF-03: sem ele, a lista pula do h1 direto para o h3 do cartão."""
    _receita_publicada()

    html = client.get(reverse("receitas:lista")).content.decode()

    assert '<h2 class="so-leitor-de-tela">Lista de receitas</h2>' in html
    assert html.index("<h1>") < html.index("so-leitor-de-tela") < html.index("<h3")
    assert "so-leitor-de-tela" in CSS_BASE


def test_filtro_ativo_diz_o_resultado_e_oferece_limpar(client: Client) -> None:
    """RF-13: com filtro ligado a abertura diz o resultado, não "todas"."""
    sobremesas = Categoria.objects.create(nome="Sobremesas")
    _receita_publicada("Pudim", sobremesas)
    _receita_publicada("Brigadeiro", sobremesas)
    _receita_publicada("Lasanha", Categoria.objects.create(nome="Massas"))

    html = client.get(
        reverse("receitas:lista"), {"categoria": sobremesas.slug}
    ).content.decode()

    assert "2 receitas" in html
    assert "<strong>Sobremesas</strong>" in html
    assert "Limpar filtro" in html
    # A meta description repete a frase; só o parágrafo de abertura importa.
    assert (
        "Todas as receitas publicadas, da mais recente" not in html.split("<main>")[1]
    )


def test_filtro_ativo_usa_o_singular_e_o_nome_da_tag(client: Client) -> None:
    """RF-13: "1 receita" no singular, e a tag aparece pelo nome, não pelo slug."""
    receita = _receita_publicada("Pudim")
    tag = Tag.objects.create(nome="sem glúten")
    receita.tags.add(tag)

    html = client.get(reverse("receitas:lista"), {"tag": tag.slug}).content.decode()

    assert re.search(r"(?<!\d)1 receita\s", html)
    assert "<strong>sem glúten</strong>" in html


def test_lista_sem_filtro_mantem_a_frase_de_sempre(client: Client) -> None:
    """RF-13: sem filtro nada muda."""
    _receita_publicada()

    html = client.get(reverse("receitas:lista")).content.decode()

    assert "Todas as receitas publicadas, da mais recente" in html.split("<main>")[1]
    assert "Limpar filtro" not in html


def test_estados_vazios_ficam_no_bloco_centrado(client: Client) -> None:
    """RF-17: lista sem receitas, busca sem resultado e home vazia."""
    lista = client.get(reverse("receitas:lista")).content.decode()
    busca = client.get(reverse("receitas:lista"), {"q": "zzzz"}).content.decode()
    home = client.get(reverse("nucleo:home")).content.decode()

    assert '<p class="estado-vazio">Nenhuma receita publicada ainda' in lista
    assert '<p class="estado-vazio">\n        Nenhuma receita encontrada' in busca
    assert '<p class="estado-vazio">Nenhuma receita publicada ainda' in home


# -----------------------------------------------------------------------------
# Receita e comentários (RF-05, RF-17)
# -----------------------------------------------------------------------------
def test_mensagem_do_comentario_aparece_na_secao_de_comentarios(
    client: Client,
) -> None:
    """RF-05: a mensagem fica acima do formulário, onde o redirect cai."""
    receita = _receita_publicada()
    client.force_login(User.objects.create_user("ana", password="senha-forte-123"))

    # Sem carimbo de tempo o envio é tratado como bot: mesmo assim vira
    # "Comentário publicado!", que é o que interessa para a posição da mensagem.
    client.post(reverse("receitas:comentar", args=[receita.slug]), {"texto": "Oi"})
    html = client.get(reverse("receitas:detalhe", args=[receita.slug])).content.decode()

    assert html.count('class="container mensagens"') == 1
    assert html.index('id="comentarios"') < html.index('class="container mensagens"')
    assert html.index('class="container mensagens"') < html.index('class="formulario"')
    assert 'role="status"' in html


def test_mensagem_de_outras_paginas_continua_no_topo_com_role_status(
    client: Client,
) -> None:
    """RF-05: só a página da receita muda de lugar; as demais seguem no topo."""
    client.force_login(User.objects.create_user("ana", password="senha-forte-123"))

    html = client.post(reverse("usuarios:sair"), follow=True).content.decode()

    assert 'class="container mensagens" role="status"' in html
    assert html.index('class="container mensagens"') < html.index("<main>")


def test_sem_comentarios_o_aviso_segue_o_alinhamento_do_titulo(client: Client) -> None:
    """RF-17: o aviso fica à esquerda, como o título "Comentários" que o abre."""
    receita = _receita_publicada()

    html = client.get(reverse("receitas:detalhe", args=[receita.slug])).content.decode()

    assert "<p>Ainda não há comentários" in html
    assert 'estado-vazio">Ainda não há comentários' not in html


# -----------------------------------------------------------------------------
# Entrar e cadastro (RF-07, RF-17)
# -----------------------------------------------------------------------------
def test_cadastro_liga_a_ajuda_aos_campos_e_nao_poe_lista_em_paragrafo(
    client: Client,
) -> None:
    """RF-07: todo aria-describedby aponta para um id; <ul> não fica em <p>."""
    html = client.get(reverse("usuarios:cadastro")).content.decode()
    ids = _Ids()
    ids.feed(html)

    assert ids.descritos, "o cadastro deveria ter campos com ajuda"
    assert [d for d in ids.descritos if d not in ids.ids] == []
    assert not re.search(r"<p[^>]*>\s*<ul", html)
    assert 'autocomplete="email"' in html


def test_ajuda_da_senha_herda_o_estilo_da_ajuda() -> None:
    """RF-07: a lista de regras da senha escapava do estilo da ajuda."""
    assert "padding-left:" in _bloco_css(CSS_BASE, ".formulario__ajuda ul")


@pytest.mark.parametrize("rota", ["usuarios:entrar", "usuarios:cadastro"])
def test_entrar_e_cadastro_usam_a_coluna_centrada(client: Client, rota: str) -> None:
    """RF-17."""
    html = client.get(reverse(rota)).content.decode()

    assert "cabecalho-pagina pagina-formulario" in html


# -----------------------------------------------------------------------------
# Páginas de erro (RF-04)
# -----------------------------------------------------------------------------
def test_404_e_a_pagina_do_projeto_em_portugues(client: Client) -> None:
    """RF-04: com DEBUG=False o Django usa o templates/404.html."""
    resposta = client.get("/isto-nao-existe/")
    html = resposta.content.decode()

    assert resposta.status_code == 404
    assert '<html lang="pt-br">' in html
    assert "Esta página não existe." in html
    assert 'name="viewport"' in html
    assert "<main>" in html
    assert f'href="{reverse("receitas:lista")}"' in html


def test_403_e_a_pagina_do_projeto_em_portugues(rf: RequestFactory) -> None:
    """RF-04: o PermissionDenied (e a falha de CSRF) usam o templates/403.html."""
    resposta = permission_denied(rf.get("/"), PermissionError())
    html = resposta.content.decode()

    assert resposta.status_code == 403
    assert "Você não pode abrir esta página." in html
    assert '<html lang="pt-br">' in html


def test_500_e_html_completo_e_nao_consulta_o_banco(
    rf: RequestFactory, django_assert_num_queries: Any
) -> None:
    """RF-04: o 500 não herda o base.html (que consulta sessão e usuário)."""
    with django_assert_num_queries(0):
        resposta = server_error(rf.get("/"))
    html = resposta.content.decode()

    assert resposta.status_code == 500
    assert '<html lang="pt-br">' in html
    assert 'name="viewport"' in html
    assert "Algo deu errado na cozinha." in html
    assert 'class="navbar"' not in html


def test_500_nao_depende_de_contexto_nem_de_url_nomeada() -> None:
    """RF-04: o template renderiza sem nenhum contexto."""
    assert "Erro 500" in render_to_string("500.html")


# -----------------------------------------------------------------------------
# Menu do celular (RF-06)
# -----------------------------------------------------------------------------
def test_menu_mobile_leva_o_foco_fecha_com_esc_e_com_clique_fora() -> None:
    """RF-06: o JavaScript tem os três comportamentos de teclado do menu."""
    assert (
        'botao.setAttribute("aria-label", "Fechar menu de navegação");' in JS_INTERACOES
    )
    assert (
        'botao.setAttribute("aria-label", "Abrir menu de navegação");' in JS_INTERACOES
    )
    assert "primeiroLink.focus();" in JS_INTERACOES
    assert 'evento.key === "Escape"' in JS_INTERACOES
    assert "fecharMenu({ devolverFoco: true });" in JS_INTERACOES
    assert "!barra.contains(evento.target)" in JS_INTERACOES
    assert "fecharMenu({ devolverFoco: false });" in JS_INTERACOES


# -----------------------------------------------------------------------------
# Home, ícone e fontes (RF-01, RF-12, RF-14)
# -----------------------------------------------------------------------------
def test_home_fala_de_receitas_e_o_django_fica_por_dentro(client: Client) -> None:
    """RF-01: o h1 é de comida; o Django aparece na seção "Por dentro"."""
    html = client.get(reverse("nucleo:home")).content.decode()
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    por_dentro = html[html.index('id="por-dentro"') :]

    assert h1
    assert "Receitas simples para todos os dias." in h1.group(1)
    assert "Django" not in h1.group(1)
    assert "Por dentro, um projeto Django" in por_dentro
    assert "github.com/ryanvmorais/blog-culinario" in por_dentro


def test_home_convida_o_anonimo_a_criar_conta_e_poupa_quem_ja_entrou(
    client: Client,
) -> None:
    """RF-01: o botão secundário só aparece para quem não está autenticado."""
    anonimo = client.get(reverse("nucleo:home")).content.decode()
    client.force_login(User.objects.create_user("ana", password="senha-forte-123"))
    logado = client.get(reverse("nucleo:home")).content.decode()

    assert "Criar minha conta" in anonimo
    assert "Criar minha conta" not in logado


def test_favicon_declarado_e_arquivo_existe(client: Client) -> None:
    """RF-12: sem ele o navegador pede /favicon.ico e recebe 404."""
    html = client.get(reverse("nucleo:home")).content.decode()

    assert 'rel="icon"' in html
    assert "img/favicon.svg" in html
    assert (RAIZ / "static/img/favicon.svg").is_file()


def test_fontes_vem_do_projeto_e_nao_do_google(client: Client) -> None:
    """RF-14: nenhuma requisição a terceiros (LGPD) e as fontes existem no disco."""
    paginas = [reverse("nucleo:home"), reverse("receitas:lista")]
    for url in paginas:
        html = client.get(url).content.decode()
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html
        assert "css/fontes.css" in html
        assert "fonts/inter-latin.woff2" in html

    assert CSS_FONTES.count("@font-face") == 2
    assert CSS_FONTES.count("font-display: swap;") == 2
    for nome in ("inter-latin.woff2", "fraunces-latin.woff2"):
        assert (RAIZ / "static/fonts" / nome).is_file()


def test_catalogo_tambem_usa_as_fontes_locais() -> None:
    """RF-14, RNF-03: o catálogo abre por file:// e usa o mesmo fontes.css."""
    catalogo = (RAIZ / "docs/design-system.html").read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in catalogo
    assert "../static/css/fontes.css" in catalogo
