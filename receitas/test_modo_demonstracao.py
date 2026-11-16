"""
Testes do modo demonstração nos comentários (spec 009, RF-06).

Estratégia de isolamento: ORM/HTTP de teste do Django, sem mock; o modo é ligado e
desligado por ``override_settings(MODO_DEMONSTRACAO=...)``. Os builders e o carimbo
válido do time-trap (spec 007) vêm de ``receitas/tests.py``, para os dois arquivos
montarem receita e envio do mesmo jeito. O cache é limpo antes de cada teste para o
limite de comentários (spec 006) não vazar entre testes.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

from blog_culinario.demonstracao import URL_REPOSITORIO

from .models import Comentario, Receita
from .tests import _carimbo_valido, _receita

pytestmark = pytest.mark.django_db

User = get_user_model()

AVISO_FIXO = "Comentários de demonstração:"
MENSAGEM_DO_MODO = "não publica comentários"


@pytest.fixture(autouse=True)
def _limpar_cache_de_limitacao() -> None:
    """Zera os contadores de limitação de taxa antes de cada teste (spec 006)."""
    cache.clear()


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------
def _leitor_logado(client: Client) -> Receita:
    """
    Cria uma receita publicada e autentica um leitor no ``client``.

    Args:
        client (Client): cliente de teste que recebe a sessão.

    Returns:
        Receita: a receita publicada, pronta para comentar.
    """
    leitor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(leitor)
    return _receita(publicado=True)


def _comentar(client: Client, receita: Receita, **kwargs: Any) -> str:
    """
    Envia um comentário que passa no time-trap e devolve o HTML final.

    Args:
        client (Client): cliente já autenticado.
        receita (Receita): receita comentada.
        **kwargs (Any): campos que sobrescrevem o POST (``texto``,
            ``endereco_web``).

    Returns:
        str: conteúdo da página depois do redirect.
    """
    dados = {"texto": "Ficou ótimo!", "carimbo_tempo": _carimbo_valido()}
    dados.update(kwargs)
    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        dados,
        follow=True,
    )
    return resposta.content.decode()


# -----------------------------------------------------------------------------
# Aviso fixo no formulário
# -----------------------------------------------------------------------------
@override_settings(MODO_DEMONSTRACAO=True)
def test_aviso_aparece_no_formulario_com_o_modo_ligado(client: Client) -> None:
    receita = _leitor_logado(client)

    conteudo = client.get(
        reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    ).content.decode()

    assert AVISO_FIXO in conteudo
    # Dentro do formulário, antes do campo de texto.
    assert conteudo.index('<form class="formulario"') < conteudo.index(AVISO_FIXO)
    assert conteudo.index(AVISO_FIXO) < conteudo.index('name="texto"')


@override_settings(MODO_DEMONSTRACAO=False)
def test_sem_aviso_com_o_modo_desligado(client: Client) -> None:
    receita = _leitor_logado(client)

    conteudo = client.get(
        reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    ).content.decode()

    assert AVISO_FIXO not in conteudo


# -----------------------------------------------------------------------------
# Envio
# -----------------------------------------------------------------------------
@override_settings(MODO_DEMONSTRACAO=True)
def test_comentario_valido_nao_e_gravado_com_o_modo_ligado(client: Client) -> None:
    receita = _leitor_logado(client)

    conteudo = _comentar(client, receita)

    assert not Comentario.objects.exists()
    assert MENSAGEM_DO_MODO in conteudo
    assert "Comentário publicado!" not in conteudo
    # O link sai como HTML, não escapado (RNF-03, ADR-2).
    assert f'<a href="{URL_REPOSITORIO}"' in conteudo


@override_settings(MODO_DEMONSTRACAO=True)
def test_honeypot_responde_a_mensagem_do_modo(client: Client) -> None:
    """O falso sucesso imita o sucesso daquele ambiente (decisão resolvida 6)."""
    receita = _leitor_logado(client)

    conteudo = _comentar(client, receita, endereco_web="http://spam.exemplo.com")

    assert not Comentario.objects.exists()
    assert MENSAGEM_DO_MODO in conteudo
    assert "Comentário publicado!" not in conteudo


@override_settings(MODO_DEMONSTRACAO=True)
def test_comentario_vazio_responde_como_hoje(client: Client) -> None:
    receita = _leitor_logado(client)

    conteudo = _comentar(client, receita, texto="")

    assert "O comentário não pode ficar vazio." in conteudo
    assert MENSAGEM_DO_MODO not in conteudo


@override_settings(MODO_DEMONSTRACAO=True)
def test_limite_de_taxa_vale_com_o_modo_ligado(client: Client) -> None:
    """Os envios recusados pelo modo também contam no limite da spec 006."""
    receita = _leitor_logado(client)
    for _ in range(5):
        _comentar(client, receita)

    conteudo = _comentar(client, receita)

    assert "Você está comentando rápido demais" in conteudo


@override_settings(MODO_DEMONSTRACAO=False)
def test_comentario_valido_e_publicado_com_o_modo_desligado(client: Client) -> None:
    receita = _leitor_logado(client)

    conteudo = _comentar(client, receita)

    assert Comentario.objects.filter(receita=receita).count() == 1
    assert "Comentário publicado!" in conteudo
