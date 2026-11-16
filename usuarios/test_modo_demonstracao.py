"""
Testes do modo demonstração no cadastro, no login e no comando da conta (spec 009).

Estratégia de isolamento: ORM/HTTP de teste do Django, sem mock; o modo é ligado e
desligado por ``override_settings(MODO_DEMONSTRACAO=...)``, que vale porque o módulo
``blog_culinario.demonstracao`` lê a setting na hora da chamada. O comando roda por
``call_command`` com a saída capturada num ``StringIO``. O cache é limpo antes de cada
teste para o limite de tentativas de login (spec 006) não vazar entre testes.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from blog_culinario.demonstracao import (
    SENHA_DEMONSTRACAO,
    URL_REPOSITORIO,
    USUARIO_DEMONSTRACAO,
)

pytestmark = pytest.mark.django_db

User = get_user_model()

LINK_REPOSITORIO = f'<a href="{URL_REPOSITORIO}"'


@pytest.fixture(autouse=True)
def _limpar_cache_de_limitacao() -> None:
    """Zera os contadores de limitação de taxa antes de cada teste (spec 006)."""
    cache.clear()


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------
def _dados_cadastro(**kwargs: Any) -> dict[str, Any]:
    """
    Payload válido para o formulário de cadastro, sobrescrevível por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default.

    Returns:
        dict[str, Any]: dados prontos para o POST em ``usuarios:cadastro``.
    """
    dados = {
        "username": "chef-teste",
        "email": "chef@example.com",
        "password1": "uma-senha-bem-forte-123",
        "password2": "uma-senha-bem-forte-123",
    }
    dados.update(kwargs)
    return dados


def _rodar_comando() -> str:
    """
    Roda ``criar_conta_demonstracao`` e devolve o que ele escreveu.

    Returns:
        str: a saída do comando.
    """
    saida = StringIO()
    call_command("criar_conta_demonstracao", stdout=saida)
    return saida.getvalue()


# -----------------------------------------------------------------------------
# Interruptor (RF-01)
# -----------------------------------------------------------------------------
def test_modo_vem_desligado_sem_a_variavel() -> None:
    """A suíte roda sem ``MODO_DEMONSTRACAO`` no ambiente, então vale o padrão."""
    assert settings.MODO_DEMONSTRACAO is False


@override_settings(MODO_DEMONSTRACAO=False)
def test_modo_desligado_nao_poe_credenciais_no_contexto(client: Client) -> None:
    resposta = client.get(reverse("usuarios:entrar"))

    assert resposta.context["modo_demonstracao"] is False
    assert "conta_demonstracao" not in resposta.context


# -----------------------------------------------------------------------------
# Cadastro (RF-02, RF-03, RNF-02, RNF-03)
# -----------------------------------------------------------------------------
@override_settings(MODO_DEMONSTRACAO=True)
def test_cadastro_mostra_o_aviso_com_o_modo_ligado(client: Client) -> None:
    conteudo = client.get(reverse("usuarios:cadastro")).content.decode()

    assert "Cadastro de demonstração:" in conteudo
    assert f'href="{reverse("usuarios:entrar")}"' in conteudo


@override_settings(MODO_DEMONSTRACAO=False)
def test_cadastro_sem_aviso_com_o_modo_desligado(client: Client) -> None:
    conteudo = client.get(reverse("usuarios:cadastro")).content.decode()

    assert "Cadastro de demonstração" not in conteudo


@override_settings(MODO_DEMONSTRACAO=True)
def test_cadastro_invalido_mostra_os_erros_de_hoje(client: Client) -> None:
    resposta = client.post(
        reverse("usuarios:cadastro"),
        _dados_cadastro(password2="outra-senha-diferente-456"),
    )

    assert resposta.status_code == 200
    assert resposta.context["form"].errors["password2"]
    assert not User.objects.filter(username="chef-teste").exists()


@override_settings(MODO_DEMONSTRACAO=True)
def test_cadastro_valido_nao_cria_conta_e_mostra_o_aviso(client: Client) -> None:
    resposta = client.post(reverse("usuarios:cadastro"), _dados_cadastro(), follow=True)

    conteudo = resposta.content.decode()
    assert not User.objects.filter(username="chef-teste").exists()
    assert not resposta.wsgi_request.user.is_authenticated
    assert resposta.redirect_chain == [(reverse("usuarios:cadastro"), 302)]
    assert "não cria contas" in conteudo
    # O link sai como HTML, não escapado (ADR-2).
    assert LINK_REPOSITORIO in conteudo


@override_settings(MODO_DEMONSTRACAO=False)
def test_cadastro_valido_com_o_modo_desligado_cria_conta(client: Client) -> None:
    client.post(reverse("usuarios:cadastro"), _dados_cadastro())

    assert User.objects.filter(username="chef-teste").exists()


# -----------------------------------------------------------------------------
# Login (RF-04)
# -----------------------------------------------------------------------------
@override_settings(MODO_DEMONSTRACAO=True)
def test_login_mostra_as_credenciais_com_o_modo_ligado(client: Client) -> None:
    conteudo = client.get(reverse("usuarios:entrar")).content.decode()

    assert "Conta de demonstração" in conteudo
    assert f"<dd>{USUARIO_DEMONSTRACAO}</dd>" in conteudo
    assert f"<dd>{SENHA_DEMONSTRACAO}</dd>" in conteudo


@override_settings(MODO_DEMONSTRACAO=False)
def test_login_sem_credenciais_com_o_modo_desligado(client: Client) -> None:
    conteudo = client.get(reverse("usuarios:entrar")).content.decode()

    assert SENHA_DEMONSTRACAO not in conteudo


@override_settings(MODO_DEMONSTRACAO=True)
def test_conta_de_demonstracao_entra_com_as_credenciais_da_tela(
    client: Client,
) -> None:
    _rodar_comando()

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": USUARIO_DEMONSTRACAO, "password": SENHA_DEMONSTRACAO},
        follow=True,
    )

    assert resposta.wsgi_request.user.is_authenticated
    assert "Bem-vindo(a) de volta" in resposta.content.decode()


# -----------------------------------------------------------------------------
# Comando criar_conta_demonstracao (RF-05, ADR-6)
# -----------------------------------------------------------------------------
@override_settings(MODO_DEMONSTRACAO=True)
def test_comando_cria_a_conta_sem_staff() -> None:
    saida = _rodar_comando()

    conta = User.objects.get(username=USUARIO_DEMONSTRACAO)
    assert conta.is_active
    assert not conta.is_staff
    assert not conta.is_superuser
    assert conta.check_password(SENHA_DEMONSTRACAO)
    assert "criada" in saida
    assert "desligado" not in saida


@override_settings(MODO_DEMONSTRACAO=True)
def test_comando_restaura_senha_e_permissoes_sem_duplicar() -> None:
    """Uma senha trocada e o staff ligado pelo Admin voltam ao esperado."""
    User.objects.create_user(
        username=USUARIO_DEMONSTRACAO,
        password="senha-trocada-999",
        is_staff=True,
        is_superuser=True,
        is_active=False,
    )

    saida = _rodar_comando()

    assert User.objects.filter(username=USUARIO_DEMONSTRACAO).count() == 1
    conta = User.objects.get(username=USUARIO_DEMONSTRACAO)
    assert conta.check_password(SENHA_DEMONSTRACAO)
    assert conta.is_active
    assert not conta.is_staff
    assert not conta.is_superuser
    assert "atualizada" in saida


@override_settings(MODO_DEMONSTRACAO=False)
def test_comando_avisa_com_o_modo_desligado() -> None:
    saida = _rodar_comando()

    assert User.objects.filter(username=USUARIO_DEMONSTRACAO).exists()
    assert "MODO_DEMONSTRACAO está desligado" in saida
