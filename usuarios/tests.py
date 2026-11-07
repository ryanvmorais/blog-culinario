"""
Testes de autenticação: cadastro, login, logout, reflexo na navbar (spec 004)
e limite de tentativas de login (spec 006).

Estratégia de isolamento: ORM/HTTP de teste do Django, sem mock — login e
logout são o comportamento nativo do ``django.contrib.auth``, exercitado
via ``Client`` como um navegador faria. O cache é limpo antes de cada teste
(fixture autouse) para os contadores de limitação de taxa não vazarem de um
teste para o outro.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import reverse

from blog_culinario.limitacao import limite_excedido

pytestmark = pytest.mark.django_db

User = get_user_model()


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
        **kwargs (Any): campos que sobrescrevem o default (``username``,
            ``password1``, etc.).

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


# -----------------------------------------------------------------------------
# Cadastro (RF-01, RF-06)
# -----------------------------------------------------------------------------
def test_cadastro_com_dados_validos_cria_e_autentica(client: Client) -> None:
    resposta = client.post(reverse("usuarios:cadastro"), _dados_cadastro(), follow=True)

    assert User.objects.filter(username="chef-teste").exists()
    assert resposta.wsgi_request.user.is_authenticated
    assert "Bem-vindo(a)" in resposta.content.decode()


def test_cadastro_com_username_duplicado_nao_cria_conta(client: Client) -> None:
    User.objects.create_user(username="chef-teste", password="outra-senha-123")

    client.post(reverse("usuarios:cadastro"), _dados_cadastro())

    assert User.objects.filter(username="chef-teste").count() == 1


def test_cadastro_com_senha_fraca_nao_cria_conta(client: Client) -> None:
    client.post(
        reverse("usuarios:cadastro"), _dados_cadastro(password1="123", password2="123")
    )

    assert not User.objects.filter(username="chef-teste").exists()


def test_cadastro_com_senhas_divergentes_nao_cria_conta(client: Client) -> None:
    client.post(
        reverse("usuarios:cadastro"),
        _dados_cadastro(password2="uma-senha-completamente-diferente"),
    )

    assert not User.objects.filter(username="chef-teste").exists()


# -----------------------------------------------------------------------------
# Login (RF-02, RF-05, RF-06)
# -----------------------------------------------------------------------------
def test_login_com_credenciais_corretas_autentica(client: Client) -> None:
    User.objects.create_user(username="chef-teste", password="uma-senha-bem-forte-123")

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "chef-teste", "password": "uma-senha-bem-forte-123"},
        follow=True,
    )

    assert resposta.wsgi_request.user.is_authenticated
    assert "Bem-vindo(a) de volta" in resposta.content.decode()


def test_login_com_credenciais_erradas_mostra_mensagem_generica(client: Client) -> None:
    User.objects.create_user(username="chef-teste", password="uma-senha-bem-forte-123")

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "chef-teste", "password": "senha-errada"},
    )

    assert not resposta.wsgi_request.user.is_authenticated
    # mensagem genérica do AuthenticationForm — não diz qual campo errou
    assert "corretos" in resposta.content.decode()


def test_login_redireciona_para_next_apos_autenticar(client: Client) -> None:
    User.objects.create_user(username="chef-teste", password="uma-senha-bem-forte-123")

    resposta = client.post(
        reverse("usuarios:entrar") + "?next=/receitas/",
        {"username": "chef-teste", "password": "uma-senha-bem-forte-123"},
    )

    assert resposta.status_code == 302
    assert resposta["Location"] == "/receitas/"


# -----------------------------------------------------------------------------
# Logout (RF-03, RF-06, ADR-2)
# -----------------------------------------------------------------------------
def test_logout_encerra_sessao(client: Client) -> None:
    usuario = User.objects.create_user(
        username="chef-teste", password="uma-senha-bem-forte-123"
    )
    client.force_login(usuario)

    resposta = client.post(reverse("usuarios:sair"), follow=True)

    assert not resposta.wsgi_request.user.is_authenticated
    assert "Você saiu da sua conta." in resposta.content.decode()


def test_logout_via_get_nao_e_permitido(client: Client) -> None:
    """``LogoutView`` só aceita POST desde o Django 4.1 (ADR-2)."""
    usuario = User.objects.create_user(
        username="chef-teste", password="uma-senha-bem-forte-123"
    )
    client.force_login(usuario)

    resposta = client.get(reverse("usuarios:sair"))

    assert resposta.status_code == 405


# -----------------------------------------------------------------------------
# Limite de tentativas de login (spec 006, RF-01, RF-03, RNF-02)
# -----------------------------------------------------------------------------
def test_login_bloqueia_a_partir_da_sexta_tentativa_no_mesmo_ip(client: Client) -> None:
    """5 tentativas consomem o limite; a 6ª é bloqueada antes de checar a senha."""
    User.objects.create_user(username="chef-teste", password="uma-senha-bem-forte-123")
    for _ in range(5):
        client.post(
            reverse("usuarios:entrar"),
            {"username": "chef-teste", "password": "senha-errada"},
        )

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "chef-teste", "password": "uma-senha-bem-forte-123"},
        follow=True,
    )

    # bloqueada mesmo com a senha correta -- prova que nem chegou a validar
    assert not resposta.wsgi_request.user.is_authenticated
    assert "Muitas tentativas de login" in resposta.content.decode()


def test_login_dois_ips_nao_compartilham_o_limite(client: Client) -> None:
    """O contador é por IP -- outro IP não é afetado pelas tentativas do primeiro."""
    User.objects.create_user(username="chef-teste", password="uma-senha-bem-forte-123")
    for _ in range(5):
        client.post(
            reverse("usuarios:entrar"),
            {"username": "chef-teste", "password": "senha-errada"},
            REMOTE_ADDR="10.0.0.1",
        )

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "chef-teste", "password": "uma-senha-bem-forte-123"},
        REMOTE_ADDR="10.0.0.2",
    )

    assert resposta.wsgi_request.user.is_authenticated


def test_limite_excedido_expira_apos_a_janela(rf: RequestFactory) -> None:
    """
    O contador zera sozinho ao fim da janela configurada (RF-03).

    Testa ``limite_excedido`` diretamente (não via view) -- a janela real do
    login é de 5 minutos, longa demais para esperar num teste.
    """
    request = rf.post("/qualquer-url/")
    request.META["REMOTE_ADDR"] = "127.0.0.1"

    for _ in range(3):
        assert limite_excedido(request, "teste-janela", 3, 1) is False
    assert limite_excedido(request, "teste-janela", 3, 1) is True

    time.sleep(1.1)

    assert limite_excedido(request, "teste-janela", 3, 1) is False


# -----------------------------------------------------------------------------
# Navbar reflete autenticação (RF-04)
# -----------------------------------------------------------------------------
def test_navbar_mostra_entrar_para_anonimo(client: Client) -> None:
    resposta = client.get(reverse("nucleo:home"))

    conteudo = resposta.content.decode()
    assert "Entrar" in conteudo
    assert "Cadastrar" in conteudo


def test_navbar_mostra_username_e_sair_para_autenticado(client: Client) -> None:
    usuario = User.objects.create_user(
        username="chef-teste", password="uma-senha-bem-forte-123"
    )
    client.force_login(usuario)

    resposta = client.get(reverse("nucleo:home"))

    conteudo = resposta.content.decode()
    assert "chef-teste" in conteudo
    assert "Sair" in conteudo
    assert "Entrar" not in conteudo
