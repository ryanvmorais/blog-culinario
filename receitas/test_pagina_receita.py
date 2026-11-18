"""
Testes da página da receita redesenhada (spec 012, adendo, RF-19 a RF-24).

Estratégia de isolamento: ``partes_do_preparo()`` é testado sem banco, numa
``Receita`` que não é salva; a página, pelo ``Client`` de teste do Django, com os
builders de ``receitas/tests.py``.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Receita, TrechoDoPreparo
from .tests import _categoria, _comentario, _receita

User = get_user_model()


def _partes(texto: str) -> list[TrechoDoPreparo]:
    """
    Divide um modo de preparo sem gravar a receita.

    Args:
        texto (str): o conteúdo do campo ``modo_de_preparo``.

    Returns:
        list[TrechoDoPreparo]: o resultado de ``partes_do_preparo()``.
    """
    return Receita(modo_de_preparo=texto).partes_do_preparo()


# -----------------------------------------------------------------------------
# RF-22 — passos numerados, sem banco
# -----------------------------------------------------------------------------
def test_paragrafos_numerados_viram_um_grupo_de_passos_sem_o_numero() -> None:
    """Parágrafos com "1." ou "1)" formam um grupo, sem o número digitado (RF-22)."""
    partes = _partes("1. Preaqueça o forno.\n\n2) Misture tudo.\n\n3. Asse.")
    assert partes == [
        TrechoDoPreparo("passos", ["Preaqueça o forno.", "Misture tudo.", "Asse."], 1)
    ]


def test_paragrafo_depois_do_ultimo_passo_vira_nota() -> None:
    """O que vem depois do último passo é nota, como a fonte da receita (RF-22)."""
    partes = _partes("1. Asse.\n\nReceita adaptada de um caderno de família.")
    assert [p.tipo for p in partes] == ["passos", "nota"]
    assert partes[1].textos == ["Receita adaptada de um caderno de família."]


def test_paragrafo_antes_dos_passos_fica_como_paragrafo() -> None:
    """Parágrafo sem número antes dos passos fica no lugar (RF-22)."""
    partes = _partes("Separe tudo antes.\n\n1. Misture.\n\n2. Asse.")
    assert [p.tipo for p in partes] == ["paragrafo", "passos"]
    assert partes[1].inicio == 1


def test_paragrafo_entre_grupos_mantem_a_contagem_dos_passos() -> None:
    """O segundo grupo continua a contagem pelo ``inicio`` (RF-22, ADR-9)."""
    partes = _partes("1. Faça a massa.\n\n2. Descanse.\n\nPara a calda:\n\n1. Derreta.")
    assert [(p.tipo, p.inicio) for p in partes] == [
        ("passos", 1),
        ("paragrafo", 1),
        ("passos", 3),
    ]
    assert partes[2].textos == ["Derreta."]


def test_numero_digitado_nao_manda_na_numeracao() -> None:
    """Os passos são numerados pela posição, não pelo número digitado (ADR-9)."""
    partes = _partes("5. Primeiro.\n\n9. Segundo.")
    assert partes == [TrechoDoPreparo("passos", ["Primeiro.", "Segundo."], 1)]


def test_quebra_de_linha_do_windows_e_paragrafos_vazios() -> None:
    """Quebra de linha do Windows e blocos em branco não criam parágrafo (RF-22)."""
    partes = _partes("1. Um.\r\n\r\n\r\n   \r\n2. Dois.\r\n")
    assert partes == [TrechoDoPreparo("passos", ["Um.", "Dois."], 1)]


def test_quebra_simples_dentro_do_passo_fica_no_mesmo_passo() -> None:
    """Só a linha em branco separa parágrafos; a quebra simples fica (RF-22)."""
    partes = _partes("1. Misture a farinha\ne o açúcar.\n\n2. Asse.")
    assert partes[0].textos == ["Misture a farinha\ne o açúcar.", "Asse."]


def test_passos_um_por_linha_sem_linha_em_branco_viram_passos() -> None:
    """Lista digitada com quebra simples: cada linha numerada é um passo (RF-22)."""
    partes = _partes("1. Separe tudo.\n2. Misture.\n3. Asse.")
    assert partes == [
        TrechoDoPreparo("passos", ["Separe tudo.", "Misture.", "Asse."], 1)
    ]


def test_linha_sem_numero_antes_dos_passos_colados_fica_como_paragrafo() -> None:
    """Uma introdução na linha de cima não engole os passos de baixo (RF-22)."""
    partes = _partes("Para a massa:\n1. Misture.\n2. Sove.")
    assert [(p.tipo, p.textos) for p in partes] == [
        ("paragrafo", ["Para a massa:"]),
        ("passos", ["Misture.", "Sove."]),
    ]


def test_linha_que_continua_o_passo_colado_fica_nele() -> None:
    """A linha sem número continua o passo de cima, como "2 xícaras" (RF-22)."""
    partes = _partes("1. Junte\n2 xícaras de farinha.\n2. Asse.")
    assert partes[0].textos == ["Junte\n2 xícaras de farinha.", "Asse."]


def test_numero_sem_espaco_depois_nao_e_passo() -> None:
    """Em "1.5 kg" não há passo: o número precisa de espaço depois (RF-22)."""
    partes = _partes("1.5 kg de farinha rende duas fornadas.")
    assert [p.tipo for p in partes] == ["paragrafo"]


def test_receita_sem_passo_numerado_fica_em_paragrafos() -> None:
    """Sem nenhum passo numerado, a receita aparece como hoje (RF-22)."""
    partes = _partes("Misture tudo.\n\nAsse por 40 minutos.")
    assert partes == [
        TrechoDoPreparo("paragrafo", ["Misture tudo.", "Asse por 40 minutos."], 1)
    ]


def test_modo_de_preparo_vazio_nao_gera_trecho() -> None:
    """Texto só com espaços não gera trecho (RF-22)."""
    assert _partes("  \n\n ") == []


def test_dividir_nao_muda_o_texto_do_campo() -> None:
    """O número sai só na exibição; o campo fica intacto (RF-22)."""
    texto = "1. Um.\r\n\r\n2. Dois."
    receita = Receita(modo_de_preparo=texto)
    receita.partes_do_preparo()
    assert receita.modo_de_preparo == texto


# -----------------------------------------------------------------------------
# Página da receita, pelo Client
# -----------------------------------------------------------------------------
def _pagina(client: Client, receita: Receita) -> str:
    """
    Abre a página de uma receita e devolve o HTML.

    Args:
        client (Client): cliente de teste, com ou sem sessão.
        receita (Receita): a receita publicada a abrir.

    Returns:
        str: o HTML da resposta.
    """
    resposta = client.get(reverse("receitas:detalhe", args=[receita.slug]))
    assert resposta.status_code == 200
    return str(resposta.content.decode())


def _titulos_de_mais_receitas(client: Client, receita: Receita) -> list[str]:
    """
    Abre a página de uma receita e devolve os títulos de "Mais receitas".

    Args:
        client (Client): cliente de teste.
        receita (Receita): a receita aberta.

    Returns:
        list[str]: os títulos, na ordem da seção.
    """
    resposta = client.get(reverse("receitas:detalhe", args=[receita.slug]))
    return [r.titulo for r in resposta.context["mais_receitas"]]


def _publicada_em(dias_atras: int, **kwargs: Any) -> Receita:
    """
    Cria uma receita publicada com a data de criação fixada.

    Args:
        dias_atras (int): quantos dias antes de agora ela foi criada.
        **kwargs (Any): campos repassados ao builder ``_receita``.

    Returns:
        Receita: a receita gravada, com ``criado_em`` ajustado.
    """
    receita = _receita(publicado=True, **kwargs)
    Receita.objects.filter(pk=receita.pk).update(
        criado_em=timezone.now() - timedelta(days=dias_atras)
    )
    receita.refresh_from_db()
    return receita


def _trecho(html: str, inicio: str, fim: str) -> str:
    """
    Recorta o HTML entre a primeira ocorrência de ``inicio`` e o ``fim`` seguinte.

    Args:
        html (str): a página inteira.
        inicio (str): marca onde o recorte começa.
        fim (str): marca onde o recorte termina, procurada depois do início.

    Returns:
        str: o pedaço do HTML, sem a marca final.
    """
    comeco = html.index(inicio)
    return html[comeco : html.index(fim, comeco)]


@pytest.mark.django_db
def test_ficha_mostra_preparo_e_rendimento_no_plural(client: Client) -> None:
    """A ficha é uma <dl> com "Preparo" e "Rende" (RF-19)."""
    ficha = _trecho(_pagina(client, _receita(publicado=True)), 'class="ficha"', "</dl>")
    assert "<dt>Preparo</dt>" in ficha and "<dd>50 min</dd>" in ficha
    assert "<dt>Rende</dt>" in ficha and "<dd>8 porções</dd>" in ficha


@pytest.mark.django_db
def test_ficha_usa_o_singular_para_uma_porcao(client: Client) -> None:
    """Uma porção sai no singular (RF-19)."""
    assert "<dd>1 porção</dd>" in _pagina(client, _receita(publicado=True, porcoes=1))


@pytest.mark.django_db
def test_autoria_vem_numa_linha_abaixo_da_ficha(client: Client) -> None:
    """Autor e data numa linha menor, depois da ficha (RF-19)."""
    autor = User.objects.create_user("chef-ana", password="senha-forte-123")
    html = _pagina(client, _receita(publicado=True, autor=autor))
    autoria = _trecho(html, 'class="receita-autoria"', "</p>")
    assert html.index("</dl>") < html.index('class="receita-autoria"')
    assert "Por chef-ana" in autoria and "publicado" in autoria


@pytest.mark.django_db
def test_autoria_sem_autor_mostra_autor_removido(client: Client) -> None:
    """Receita sem autor continua dizendo "Autor removido" (spec 002, RF-03)."""
    html = _pagina(client, _receita(publicado=True, autor=None))
    assert "Por Autor removido" in html


@pytest.mark.django_db
def test_ingredientes_num_cartao_um_por_linha_sem_linha_vazia(client: Client) -> None:
    """Cada linha não vazia é um item do cartão de ingredientes (RF-20, ADR-12)."""
    receita = _receita(publicado=True, ingredientes="2 ovos\n\n  \n1 xícara de leite")
    cartao = _trecho(_pagina(client, receita), 'class="ingredientes"', "</section>")
    assert 'tabindex="0"' in cartao
    assert cartao.count("<li>") == 2
    assert "<li>2 ovos</li>" in cartao and "<li>1 xícara de leite</li>" in cartao


@pytest.mark.django_db
def test_ingredientes_vem_antes_do_modo_de_preparo(client: Client) -> None:
    """No HTML, o cartão vem antes do preparo: a ordem do celular (RF-21)."""
    html = _pagina(client, _receita(publicado=True))
    assert html.index('class="ingredientes"') < html.index('class="preparo"')


@pytest.mark.django_db
def test_passos_viram_lista_ordenada_e_a_fonte_vira_nota(client: Client) -> None:
    """Os passos formam um <ol> sem o número digitado; a fonte é nota (RF-22)."""
    receita = _receita(
        publicado=True,
        modo_de_preparo=(
            "1. Preaqueça o forno.\n\n2. Asse <b>bem</b>.\n\nFonte: caderno."
        ),
    )
    html = _pagina(client, receita)
    assert '<ol class="passos" start="1">' in html
    assert "<li>Preaqueça o forno.</li>" in html
    assert "1. Preaqueça" not in html
    assert "Asse &lt;b&gt;bem&lt;/b&gt;." in html  # o texto continua escapado
    assert '<p class="preparo-nota">Fonte: caderno.</p>' in html


@pytest.mark.django_db
def test_preparo_sem_passo_numerado_fica_em_paragrafos(client: Client) -> None:
    """Sem passo numerado, nada de lista: parágrafos, como antes (RF-22)."""
    preparo = _trecho(
        _pagina(client, _receita(publicado=True)), 'class="preparo"', "</section>"
    )
    assert "<ol" not in preparo
    assert "<p>Bata tudo no liquidificador" in preparo


@pytest.mark.django_db
def test_anonimo_sem_comentarios_ve_o_convite_com_botao(client: Client) -> None:
    """Sem login e sem comentários: o cartão e o botão de login (RF-23)."""
    receita = _receita(publicado=True)
    convite = _trecho(_pagina(client, receita), 'class="convite-comentar"', "</div>")
    destino = (
        reverse("usuarios:entrar")
        + "?next="
        + reverse("receitas:detalhe", args=[receita.slug])
    )
    assert "Ainda não há comentários. Seja o primeiro a comentar!" in convite
    assert f'href="{destino}">Entrar para comentar</a>' in convite


@pytest.mark.django_db
def test_anonimo_com_comentarios_ve_o_convite_depois_da_lista(client: Client) -> None:
    """Com comentários, o convite vem depois deles, com outra frase (RF-23)."""
    html = _pagina(client, _comentario().receita)
    convite = _trecho(html, 'class="convite-comentar"', "</div>")
    assert html.index('class="comentario"') < html.index('class="convite-comentar"')
    assert "Entre para deixar um comentário." in convite
    assert "Entrar para comentar" in convite


@pytest.mark.django_db
def test_com_login_a_secao_de_comentarios_fica_como_antes(client: Client) -> None:
    """Com login: o estado vazio e o formulário, sem o convite (RF-23)."""
    client.force_login(User.objects.create_user("leitor", password="senha-forte-123"))
    html = _pagina(client, _receita(publicado=True))
    assert "convite-comentar" not in html
    assert "<p>Ainda não há comentários. Seja o primeiro a comentar!</p>" in html
    assert 'class="formulario"' in html


@pytest.mark.django_db
def test_mais_receitas_traz_a_mesma_categoria_primeiro(client: Client) -> None:
    """A mesma categoria vem primeiro, mais recente antes; depois as outras (RF-24)."""
    doces = _categoria(nome="Doces")
    salgados = _categoria(nome="Salgados")
    aberta = _publicada_em(10, titulo="Pudim", categoria=doces)
    _publicada_em(1, titulo="Coxinha", categoria=salgados)
    _publicada_em(5, titulo="Brigadeiro", categoria=doces)
    _publicada_em(3, titulo="Quindim", categoria=doces)

    assert _titulos_de_mais_receitas(client, aberta) == [
        "Quindim",
        "Brigadeiro",
        "Coxinha",
    ]


@pytest.mark.django_db
def test_mais_receitas_sem_a_aberta_sem_rascunho_e_no_maximo_3(client: Client) -> None:
    """Nem a receita aberta nem rascunho entram, e o limite é 3 (RF-24)."""
    aberta = _publicada_em(10, titulo="Aberta")
    for dia in range(1, 6):
        _publicada_em(dia, titulo=f"Outra {dia}")
    _receita(titulo="Rascunho", publicado=False)

    assert _titulos_de_mais_receitas(client, aberta) == [
        "Outra 1",
        "Outra 2",
        "Outra 3",
    ]


@pytest.mark.django_db
def test_mais_receitas_some_sem_outra_receita_publicada(client: Client) -> None:
    """Sozinha no blog, a receita não mostra a seção (RF-24)."""
    html = _pagina(client, _receita(publicado=True))
    assert "Mais receitas" not in html
    assert "Continue cozinhando" not in html


@pytest.mark.django_db
def test_mais_receitas_mostra_cartoes_com_capa_lazy(client: Client) -> None:
    """A seção usa o cartão de sempre, com o rótulo e o h2 (RF-24, RNF-11)."""
    aberta = _publicada_em(2, titulo="Aberta")
    _publicada_em(1, titulo="Vizinha", imagem_capa="receitas/capas/vizinha.webp")
    html = _pagina(client, aberta)
    secao = html[html.index('<span class="rotulo">Continue cozinhando</span>') :]
    assert ">Mais receitas</h2>" in secao
    assert 'class="cartao-receita"' in secao
    assert 'loading="lazy"' in secao


@pytest.mark.django_db
def test_capa_tem_alt_vazio_porque_o_titulo_vem_logo_depois(client: Client) -> None:
    """Com o título no alt, o leitor de tela lia o nome duas vezes seguidas."""
    receita = _receita(publicado=True, imagem_capa="receitas/capas/capa.webp")
    html = _pagina(client, receita)
    capa = re.search(r'<img class="receita-detalhe__capa"[^>]*>', html)
    assert capa is not None
    assert 'alt=""' in capa.group(0)


@pytest.mark.django_db
@pytest.mark.parametrize("com_login", [False, True])
def test_consultas_da_receita_nao_crescem_com_o_blog(
    client: Client, com_login: bool
) -> None:
    """O número de consultas é o mesmo com 2 e com 12 receitas (RNF-08)."""
    if com_login:
        client.force_login(
            User.objects.create_user("leitor", password="senha-forte-123")
        )
    aberta = _publicada_em(30, titulo="Aberta")
    _publicada_em(1, titulo="Primeira outra")
    url = reverse("receitas:detalhe", args=[aberta.slug])

    with CaptureQueriesContext(connection) as poucas:
        client.get(url)
    for dia in range(2, 12):
        _comentario(receita=_publicada_em(dia, titulo=f"Receita {dia}"))
        _comentario(receita=aberta)
    with CaptureQueriesContext(connection) as muitas:
        client.get(url)

    assert len(muitas) == len(poucas)
