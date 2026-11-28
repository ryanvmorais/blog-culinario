"""
Testes dos adendos da spec 006: contador por rede, teto do cache, login do
Admin e registro no log.

Ficam no ``nucleo`` porque cruzam os apps: a chave do contador e o cache valem
para todo formulário limitado, e o login do Admin divide o contador com o
login público de ``usuarios``.

Estratégia de isolamento: ``Client`` e ``RequestFactory`` do Django, sem mock.
O cache de cada teste já fica numa pasta temporária própria (``conftest.py``),
com o ``CACHES`` do projeto, ``MAX_ENTRIES`` inclusive; a trava de origem fica
desligada, então o IP do visitante é o ``REMOTE_ADDR`` do pedido de teste. O
log é lido pelo ``caplog`` do pytest, no logger ``blog_culinario.limitacao``.
"""

from __future__ import annotations

import logging
import pickle
import time

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import path, reverse
from pytest_django.fixtures import Settings

from blog_culinario.limitacao import (
    LIMITE_LOGIN,
    _identificador_de_rede,
    limite_excedido,
)
from blog_culinario.site_admin import SiteAdminComLimite
from receitas.tests import _carimbo_valido, _receita

pytestmark = pytest.mark.django_db

User = get_user_model()

SENHA_DA_EQUIPE = "uma-senha-bem-forte-123"

# Rotas do teste que monta o Admin fora do ADMIN_URL: o limite acompanha o
# site do Admin, não o caminho (ADR-5). Usadas só via ROOT_URLCONF.
urlpatterns = [path("painel-de-teste/", admin.site.urls)]


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------


def _tentar(ip: str, chave: str = "login") -> bool:
    """
    Conta uma tentativa do IP dado no limite do login.

    Args:
        ip (str): ``REMOTE_ADDR`` do pedido de teste.
        chave (str): namespace do limite. Padrão: ``"login"``.

    Returns:
        bool: o que o ``limite_excedido()`` devolveu.
    """
    pedido = RequestFactory().post("/", REMOTE_ADDR=ip)
    return limite_excedido(pedido, chave, limite=LIMITE_LOGIN, janela_segundos=300)


def _esgotar(ip: str) -> None:
    """
    Gasta todas as tentativas do login do IP dado.

    Args:
        ip (str): ``REMOTE_ADDR`` do pedido de teste.
    """
    for _ in range(LIMITE_LOGIN):
        assert not _tentar(ip)


# -----------------------------------------------------------------------------
# Identificador de rede (RF-06)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("2001:db8:1:2::a", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:ffff", "2001:db8:1:2::/64"),
        ("2001:db8:1:3::a", "2001:db8:1:3::/64"),
        ("desconhecido", "desconhecido"),
    ],
)
def test_identificador_de_rede(ip: str, esperado: str) -> None:
    """IPv4 como está, IPv4 dentro do IPv6 vira IPv4, IPv6 vira o /64 dele."""
    assert _identificador_de_rede(ip) == esperado


def test_enderecos_do_mesmo_64_dividem_o_contador() -> None:
    """O limite esgotado num endereço do /64 vale para outro endereço do bloco."""
    _esgotar("2001:db8:1:2::a")

    assert _tentar("2001:db8:1:2::b")


def test_redes_64_diferentes_tem_contadores_proprios() -> None:
    """O /64 vizinho não herda as tentativas do primeiro."""
    _esgotar("2001:db8:1:2::a")

    assert not _tentar("2001:db8:1:3::a")


def test_ipv4_dentro_do_ipv6_divide_o_contador_do_ipv4() -> None:
    """``::ffff:a.b.c.d`` e ``a.b.c.d`` são o mesmo visitante."""
    _esgotar("203.0.113.7")

    assert _tentar("::ffff:203.0.113.7")


def test_login_de_enderecos_do_mesmo_64_divide_o_limite(client: Client) -> None:
    """De ponta a ponta: o login público recusa outro endereço do mesmo /64."""
    url = "/usuarios/entrar/"
    dados = {"username": "ninguem", "password": "senha-errada"}
    for _ in range(LIMITE_LOGIN):
        client.post(url, dados, REMOTE_ADDR="2001:db8:1:2::a")

    resposta = client.post(url, dados, REMOTE_ADDR="2001:db8:1:2::b", follow=True)

    assert "Muitas tentativas de login" in resposta.content.decode()


# -----------------------------------------------------------------------------
# Teto do cache (RF-07)
# -----------------------------------------------------------------------------


def test_contador_ativo_sobrevive_a_muitos_contadores_novos() -> None:
    """
    Com o teto padrão do Django (300), os contadores novos apagariam arquivos ao
    acaso; com o do projeto, o contador esgotado continua recusando.
    """
    _esgotar("198.51.100.1")

    for numero in range(600):
        _tentar(f"10.0.{numero // 256}.{numero % 256}")

    assert _tentar("198.51.100.1")


# -----------------------------------------------------------------------------
# Login do Admin (RF-04)
# -----------------------------------------------------------------------------


def _criar_equipe() -> None:
    """Cria uma conta de staff com a ``SENHA_DA_EQUIPE``."""
    User.objects.create_user(username="equipe", password=SENHA_DA_EQUIPE, is_staff=True)


def _errar_login(client: Client, url: str, vezes: int = LIMITE_LOGIN) -> None:
    """
    Faz tentativas de login com a senha errada.

    Args:
        client (Client): cliente de teste.
        url (str): a tela de login (do Admin ou pública).
        vezes (int): quantas tentativas. Padrão: o limite do login.
    """
    for _ in range(vezes):
        client.post(url, {"username": "equipe", "password": "senha-errada"})


def test_site_do_admin_e_o_do_projeto() -> None:
    """O ``default_site`` do ``ConfigAdmin`` vale para o ``admin.site``."""
    assert isinstance(admin.site, SiteAdminComLimite)


def test_login_do_admin_recusa_acima_do_limite(client: Client) -> None:
    """Acima do limite, nem a senha certa entra: a tentativa não chega a validar."""
    _criar_equipe()
    url = reverse("admin:login")
    _errar_login(client, url)

    resposta = client.post(
        url, {"username": "equipe", "password": SENHA_DA_EQUIPE}, follow=True
    )

    assert not resposta.wsgi_request.user.is_authenticated
    assert "Muitas tentativas de login" in resposta.content.decode()


def test_login_do_admin_abaixo_do_limite_entra(client: Client) -> None:
    """Com tentativas sobrando, a equipe entra no Admin como no Django."""
    _criar_equipe()
    url = reverse("admin:login")
    _errar_login(client, url, vezes=LIMITE_LOGIN - 1)

    # O formulário do Admin manda o ``next`` num campo oculto; sem ele, o
    # LoginView cairia no LOGIN_REDIRECT_URL do site (a home).
    dados = {
        "username": "equipe",
        "password": SENHA_DA_EQUIPE,
        "next": reverse("admin:index"),
    }
    resposta = client.post(url, dados, follow=True)

    assert resposta.wsgi_request.user.is_staff
    assert resposta.redirect_chain[-1][0] == reverse("admin:index")


def test_recusa_mantem_o_next(client: Client) -> None:
    """A recusa volta para a mesma tela, com o ``?next=`` de antes."""
    url = f"{reverse('admin:login')}?next={reverse('admin:index')}"
    _errar_login(client, url)

    resposta = client.post(url, {"username": "equipe", "password": "x"})

    assert resposta.status_code == 302
    assert resposta["Location"] == url


def test_limite_esgotado_no_admin_recusa_o_login_publico(client: Client) -> None:
    """As duas telas dividem o contador ``"login"``."""
    _criar_equipe()
    _errar_login(client, reverse("admin:login"))

    resposta = client.post(
        reverse("usuarios:entrar"),
        {"username": "equipe", "password": SENHA_DA_EQUIPE},
        follow=True,
    )

    assert not resposta.wsgi_request.user.is_authenticated
    assert "Muitas tentativas de login" in resposta.content.decode()


def test_limite_esgotado_no_login_publico_recusa_o_admin(client: Client) -> None:
    """O contrário também: o login público esgotado vale no Admin."""
    _criar_equipe()
    _errar_login(client, reverse("usuarios:entrar"))

    resposta = client.post(
        reverse("admin:login"),
        {"username": "equipe", "password": SENHA_DA_EQUIPE},
        follow=True,
    )

    assert not resposta.wsgi_request.user.is_authenticated


def test_get_no_login_do_admin_nao_soma(client: Client) -> None:
    """Abrir a tela muitas vezes não gasta tentativas."""
    _criar_equipe()
    url = reverse("admin:login")
    for _ in range(LIMITE_LOGIN * 2):
        client.get(url)

    resposta = client.post(
        url, {"username": "equipe", "password": SENHA_DA_EQUIPE}, follow=True
    )

    assert resposta.wsgi_request.user.is_staff


def test_limite_acompanha_o_admin_em_outro_caminho(
    client: Client, settings: Settings
) -> None:
    """Montado fora do ``ADMIN_URL``, o login do Admin continua limitado."""
    settings.ROOT_URLCONF = __name__
    _criar_equipe()
    url = "/painel-de-teste/login/"
    _errar_login(client, url)

    resposta = client.post(url, {"username": "equipe", "password": SENHA_DA_EQUIPE})

    assert resposta.status_code == 302
    assert resposta["Location"] == url
    assert not client.session.get("_auth_user_id")


# -----------------------------------------------------------------------------
# Teto e janela de cada formulário (spec 006, RF-01 a RF-03, adendo RF-05)
# -----------------------------------------------------------------------------

# Os números ficam escritos aqui, e não importados das views: comparados com a
# própria constante, um limite ou uma janela trocados passariam sem falha.


def _validade_do_contador(chave: str) -> float:
    """
    Lê quantos segundos faltam para o contador do visitante de teste expirar.

    Args:
        chave (str): namespace do limite (``"login"``, ``"cadastro"``...).

    Returns:
        float: segundos até a validade gravada no arquivo do contador.
    """
    # _key_to_file é interno do FileBasedCache e não está nos stubs do Django.
    arquivo = cache._key_to_file(f"limite:{chave}:127.0.0.1")  # type: ignore[attr-defined]
    with open(arquivo, "rb") as conteudo:
        validade: float = pickle.load(conteudo)
    return validade - time.time()


def _postar_comentario(client: Client) -> None:
    """
    Comenta numa receita nova com um leitor autenticado e o carimbo válido.

    Args:
        client (Client): cliente de teste.
    """
    client.force_login(User.objects.create_user(username="leitor", password="x"))
    receita = _receita(publicado=True)
    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Ficou ótimo!", "carimbo_tempo": _carimbo_valido()},
    )


@pytest.mark.parametrize(
    ("chave", "janela", "enviar"),
    [
        ("login", 300, lambda c: c.post(reverse("usuarios:entrar"), {})),
        ("login", 300, lambda c: c.post(reverse("admin:login"), {})),
        ("cadastro", 3600, lambda c: c.post(reverse("usuarios:cadastro"), {})),
        ("comentario", 60, _postar_comentario),
    ],
    ids=["login", "login-do-admin", "cadastro", "comentario"],
)
def test_cada_formulario_conta_na_propria_janela(
    client: Client, chave: str, janela: int, enviar: object
) -> None:
    """A primeira tentativa abre o contador com a janela do formulário."""
    assert callable(enviar)
    enviar(client)

    assert _validade_do_contador(chave) == pytest.approx(janela, abs=5)


def test_login_publico_aceita_a_quinta_tentativa_e_recusa_a_sexta(
    client: Client,
) -> None:
    _criar_equipe()
    url = reverse("usuarios:entrar")
    _errar_login(client, url, vezes=4)
    certo = {"username": "equipe", "password": SENHA_DA_EQUIPE}

    client.post(url, certo)
    assert client.session.get("_auth_user_id")

    client.logout()
    resposta = client.post(url, certo, follow=True)
    assert not client.session.get("_auth_user_id")
    assert "Muitas tentativas de login" in resposta.content.decode()


def test_cadastro_aceita_o_decimo_envio_e_recusa_o_decimo_primeiro(
    client: Client,
) -> None:
    def dados(nome: str) -> dict[str, str]:
        return {
            "username": nome,
            "password1": "uma-senha-bem-forte-123",
            "password2": "uma-senha-bem-forte-123",
        }

    url = reverse("usuarios:cadastro")
    for _ in range(9):
        client.post(url, {"username": "x"})

    client.post(url, dados("decimo"))
    assert User.objects.filter(username="decimo").exists()

    client.logout()
    resposta = client.post(url, dados("decimo-primeiro"), follow=True)
    assert not User.objects.filter(username="decimo-primeiro").exists()
    assert "Muitas tentativas de cadastro" in resposta.content.decode()


# -----------------------------------------------------------------------------
# Registro no log (adendo 2, RF-09, RNF-06)
# -----------------------------------------------------------------------------

# Valores fixos e fáceis de achar numa string: o teste do RNF-06 confere que
# nem o IP do pedido nem o usuário digitado aparecem na linha do log.
IP_DO_TESTE = "203.0.113.9"
USUARIO_DIGITADO = "usuario-digitado-no-teste"


def _linhas_do_limite(caplog: pytest.LogCaptureFixture) -> list[str]:
    """
    Devolve as mensagens que o ``limitacao.py`` mandou ao log.

    Args:
        caplog (pytest.LogCaptureFixture): fixture de captura do pytest.

    Returns:
        list[str]: as mensagens do logger ``blog_culinario.limitacao``.
    """
    return [
        r.getMessage() for r in caplog.records if r.name == "blog_culinario.limitacao"
    ]


def _tentar_login(client: Client) -> None:
    """
    Faz uma tentativa de login errada, com IP e usuário fixos.

    Args:
        client (Client): cliente de teste.
    """
    client.post(
        "/usuarios/entrar/",
        {"username": USUARIO_DIGITADO, "password": "senha-errada"},
        REMOTE_ADDR=IP_DO_TESTE,
    )


def test_primeira_recusa_da_janela_vai_para_o_log(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    """Nada abaixo do limite, uma linha na primeira recusa, nenhuma depois."""
    caplog.set_level(logging.WARNING, logger="blog_culinario.limitacao")
    for _ in range(LIMITE_LOGIN):
        _tentar_login(client)
    assert _linhas_do_limite(caplog) == []

    _tentar_login(client)
    _tentar_login(client)

    assert _linhas_do_limite(caplog) == ["limite atingido: login /usuarios/entrar/"]


def test_linha_do_log_nao_tem_dado_do_visitante(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    """Nem o IP nem o usuário digitado entram na linha (RNF-06)."""
    caplog.set_level(logging.WARNING, logger="blog_culinario.limitacao")
    for _ in range(LIMITE_LOGIN + 1):
        _tentar_login(client)

    (linha,) = _linhas_do_limite(caplog)

    assert IP_DO_TESTE not in linha
    assert USUARIO_DIGITADO not in linha


def test_recusa_do_cadastro_vai_para_o_log(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    """Cada limite se identifica pelo nome: o do cadastro sai como ``cadastro``."""
    caplog.set_level(logging.WARNING, logger="blog_culinario.limitacao")
    for _ in range(11):
        client.post("/usuarios/cadastro/", {"username": "x"})

    assert _linhas_do_limite(caplog) == [
        "limite atingido: cadastro /usuarios/cadastro/"
    ]
