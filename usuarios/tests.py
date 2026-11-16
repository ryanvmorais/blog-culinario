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

import re
import time
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.http import HttpResponseBase
from django.test import Client, RequestFactory
from django.urls import reverse
from pytest_django.fixtures import Settings

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


def test_cadastro_nao_mostra_ajuda_no_campo_de_usuario(client: Client) -> None:
    # A ajuda padrão do Django ("150 caracteres ou menos...") saiu da tela.
    pagina = client.get(reverse("usuarios:cadastro")).content.decode()

    campo = re.search(r'<input[^>]*name="username"[^>]*>', pagina)
    assert campo is not None
    assert "aria-describedby" not in campo.group(0)
    assert "id_username_helptext" not in pagina
    assert "150 caracteres" not in pagina


def test_cadastro_com_username_invalido_segue_recusado(client: Client) -> None:
    # Sem a ajuda, a regra do nome continua: o erro aparece no envio.
    resposta = client.post(
        reverse("usuarios:cadastro"), _dados_cadastro(username="chef com espaço")
    )

    assert not User.objects.filter(username="chef com espaço").exists()
    assert resposta.context["form"].errors["username"]
    assert "formulario__erro" in resposta.content.decode()


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
# Limite no login do Admin (mesmo contador do login do site)
# -----------------------------------------------------------------------------
URL_LOGIN_ADMIN = "/admin/login/"


def _equipe() -> AbstractBaseUser:
    """
    Cria uma conta da equipe, que pode entrar no Admin.

    Returns:
        AbstractBaseUser: o usuário criado, com ``is_staff=True``.
    """
    return User.objects.create_user(
        username="editor", password="uma-senha-bem-forte-123", is_staff=True
    )


def _post_admin(client: Client, senha: str, next_: str = "/admin/") -> HttpResponseBase:
    """
    Envia o formulário de login do Admin.

    Args:
        client (Client): cliente de teste.
        senha (str): senha enviada para a conta ``editor``.
        next_ (str, optional): destino depois do login. Padrão: ``"/admin/"``.

    Returns:
        HttpResponseBase: a resposta ao POST, sem seguir redirecionamentos.
    """
    return client.post(
        f"{URL_LOGIN_ADMIN}?next={next_}",
        {"username": "editor", "password": senha, "next": next_},
    )


def test_login_do_admin_bloqueia_a_sexta_tentativa_mesmo_com_a_senha_certa(
    client: Client,
) -> None:
    _equipe()
    for _ in range(5):
        # Senha errada: o Admin volta a própria tela com o erro (200).
        assert _post_admin(client, "senha-errada").status_code == 200

    resposta = _post_admin(client, "uma-senha-bem-forte-123", next_="/admin/receitas/")

    # Recusada antes de conferir a senha: ninguém entra, e o ?next= continua.
    assert resposta.status_code == 302
    assert resposta["Location"] == f"{URL_LOGIN_ADMIN}?next=/admin/receitas/"
    pagina = client.get(resposta["Location"]).content.decode()
    assert "Muitas tentativas de login" in pagina
    assert "_auth_user_id" not in client.session


def test_login_do_admin_abaixo_do_limite_entra_normalmente(client: Client) -> None:
    _equipe()
    resposta = _post_admin(client, "uma-senha-bem-forte-123")

    assert resposta.status_code == 302
    assert resposta["Location"] == "/admin/"
    assert "_auth_user_id" in client.session


def test_login_do_site_e_do_admin_dividem_o_contador(client: Client) -> None:
    # Alternar entre os dois logins não dobra as tentativas da janela.
    _equipe()
    for _ in range(3):
        client.post(
            reverse("usuarios:entrar"), {"username": "editor", "password": "errada"}
        )
    for _ in range(2):
        _post_admin(client, "senha-errada")

    assert _post_admin(client, "uma-senha-bem-forte-123").status_code == 302
    assert "_auth_user_id" not in client.session
    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "editor", "password": "uma-senha-bem-forte-123"},
        follow=True,
    )
    assert "Muitas tentativas de login" in resposta.content.decode()


def test_abrir_a_tela_de_login_do_admin_nao_conta_tentativa(client: Client) -> None:
    _equipe()
    for _ in range(10):
        assert client.get(URL_LOGIN_ADMIN).status_code == 200

    _post_admin(client, "uma-senha-bem-forte-123")
    assert "_auth_user_id" in client.session


def test_login_do_admin_conta_por_visitante_atras_da_cloudflare(
    client: Client, settings: Settings
) -> None:
    # Com a trava de origem, dois visitantes atrás do mesmo proxy não dividem
    # o limite: cada um conta pelo próprio CF-Connecting-IP (spec 011).
    settings.ORIGEM_SEGREDOS = ("segredo-de-teste",)
    _equipe()
    cabecalhos = {"x-origin-verify": "segredo-de-teste"}
    for _ in range(5):
        client.post(
            URL_LOGIN_ADMIN,
            {"username": "editor", "password": "senha-errada"},
            headers={**cabecalhos, "cf-connecting-ip": "198.51.100.1"},
        )

    client.post(
        URL_LOGIN_ADMIN,
        {"username": "editor", "password": "uma-senha-bem-forte-123"},
        headers={**cabecalhos, "cf-connecting-ip": "198.51.100.2"},
    )
    assert "_auth_user_id" in client.session


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
