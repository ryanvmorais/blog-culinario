"""
Testes das views institucionais: home (spec 002, RF-06).

Estratégia de isolamento: ORM/HTTP de teste do Django, sem mock.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from receitas.models import Categoria, Receita

pytestmark = pytest.mark.django_db


def _receita_publicada(titulo: str = "Bolo de cenoura") -> Receita:
    """
    Cria uma receita publicada mínima, para os testes da home.

    Args:
        titulo (str, optional): título da receita. Padrão: ``"Bolo de cenoura"``.

    Returns:
        Receita: instância já persistida, com ``publicado=True``.
    """
    categoria = Categoria.objects.create(nome="Sobremesas")
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


# -----------------------------------------------------------------------------
# Home (RF-06)
# -----------------------------------------------------------------------------
def test_home_mostra_receitas_publicadas_recentes(client: Client) -> None:
    receita = _receita_publicada()

    resposta = client.get(reverse("nucleo:home"))

    assert receita.titulo in resposta.content.decode()


def test_home_sem_receitas_publicadas_mostra_mensagem_de_em_breve(
    client: Client,
) -> None:
    resposta = client.get(reverse("nucleo:home"))

    assert "Nenhuma receita publicada ainda" in resposta.content.decode()
