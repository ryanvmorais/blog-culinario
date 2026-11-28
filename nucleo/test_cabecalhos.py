"""
Testes dos cabeçalhos de segurança da resposta (spec 011, RF-16 e RF-17).

Cobrem a Content-Security-Policy nativa do Django (``SECURE_CSP``) e o
``Permissions-Policy`` do ``blog_culinario/cabecalhos.py``, lidos na resposta e
não no settings: um nome de configuração errado deixaria o cabeçalho de fora sem
que um teste de configuração acusasse. Nas páginas públicas, a política é fixa e
o HTML não tem nada inline; no Admin, o ``<style>`` e o ``<script>`` inline só
passam com o nonce do pedido.

Estratégia de isolamento: ORM e HTTP de teste do Django, sem mock nem rede.
"""

from __future__ import annotations

import re

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.test import Client, RequestFactory
from django.urls import reverse

from blog_culinario.cabecalhos import PermissionsPolicyMiddleware
from receitas.models import Categoria, Receita

# Política esperada em toda página pública, diretiva por diretiva.
POLITICA_PUBLICA = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "img-src": ["'self'"],
    "font-src": ["'self'"],
    "base-uri": ["'none'"],
    "form-action": ["'self'"],
    "object-src": ["'none'"],
    "frame-ancestors": ["'none'"],
}

# Escrita aqui, e não importada do cabecalhos.py: comparada com a constante do
# próprio módulo, a política perderia um recurso sem nenhum teste acusar.
PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)

# Código que roda sem vir de um arquivo: <script> sem src, <style>, atributo
# style="" e atributo de evento (onclick="" etc.).
SCRIPT_INLINE = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>", re.IGNORECASE)
ESTILO_INLINE = re.compile(r"<style[^>]*>", re.IGNORECASE)
ATRIBUTO_INLINE = re.compile(r"\s(style|on[a-z]+)\s*=", re.IGNORECASE)
NONCE = re.compile(r'\snonce="([^"]*)"')


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------


def _receita() -> Receita:
    """
    Cria uma receita publicada mínima, para a lista e o detalhe.

    Returns:
        Receita: instância persistida.
    """
    categoria = Categoria.objects.create(nome="Sobremesas")
    return Receita.objects.create(
        titulo="Bolo de cenoura",
        resumo="Resumo do bolo.",
        ingredientes="1 ingrediente",
        modo_de_preparo="Misture tudo.",
        tempo_preparo_minutos=10,
        porcoes=1,
        categoria=categoria,
        publicado=True,
    )


def _politica(resposta: HttpResponseBase) -> dict[str, list[str]]:
    """
    Lê o cabeçalho ``Content-Security-Policy`` como diretiva → valores.

    Args:
        resposta (HttpResponseBase): resposta do client de teste.

    Returns:
        dict[str, list[str]]: os valores de cada diretiva, na ordem do cabeçalho.
    """
    return {
        partes[0]: partes[1:]
        for partes in (
            d.split() for d in resposta["Content-Security-Policy"].split(";")
        )
        if partes
    }


def _paginas_publicas() -> list[tuple[str, int]]:
    """
    Lista as páginas públicas com o status esperado, depois de criar a receita.

    Returns:
        list[tuple[str, int]]: caminho e status de cada página.
    """
    receita = _receita()
    return [
        (reverse("nucleo:home"), 200),
        (reverse("receitas:lista"), 200),
        (reverse("receitas:detalhe", args=[receita.slug]), 200),
        (reverse("usuarios:entrar"), 200),
        (reverse("usuarios:cadastro"), 200),
        ("/pagina-que-nao-existe/", 404),
    ]


# ---------------------------------------------------------------------------
# Os padrões de inline
# ---------------------------------------------------------------------------

# As páginas do site não têm nada inline, então os testes abaixo esperam zero
# casamentos; um padrão que nunca casasse também daria zero. Cada padrão acusa
# o que procura e deixa passar o vizinho parecido.


@pytest.mark.parametrize(
    ("padrao", "acusa", "deixa_passar"),
    [
        (SCRIPT_INLINE, "<script>alert(1)</script>", '<script src="/static/a.js">'),
        (SCRIPT_INLINE, '<SCRIPT type="module">', '<script defer src="/a.js">'),
        (ESTILO_INLINE, "<style>p{}</style>", '<link rel="stylesheet" href="/a.css">'),
        (ESTILO_INLINE, '<style media="print">', "<p>style</p>"),
        (ATRIBUTO_INLINE, '<p style="color: red">', '<p data-style="x">'),
        (ATRIBUTO_INLINE, '<a onclick="f()">', '<a class="onclick">'),
        (ATRIBUTO_INLINE, '<img onerror = "f()">', '<img alt="onerror">'),
    ],
)
def test_padrao_de_inline_acusa_o_que_procura(
    padrao: re.Pattern[str], acusa: str, deixa_passar: str
) -> None:
    assert padrao.search(acusa)
    assert not padrao.search(deixa_passar)


# ---------------------------------------------------------------------------
# Páginas públicas
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_paginas_publicas_enviam_a_csp_sem_nonce(client: Client) -> None:
    """Sem nada inline, o nonce nem é gerado e a política é a mesma a cada pedido."""
    for caminho, status in _paginas_publicas():
        resposta = client.get(caminho)
        assert resposta.status_code == status, caminho
        assert _politica(resposta) == POLITICA_PUBLICA, caminho


@pytest.mark.django_db
def test_paginas_publicas_nao_tem_script_nem_estilo_inline(client: Client) -> None:
    """RNF-02: o que a CSP bloquearia nem chega ao HTML do visitante."""
    for caminho, _status in _paginas_publicas():
        pagina = client.get(caminho).content.decode()
        assert not SCRIPT_INLINE.search(pagina), caminho
        assert not ESTILO_INLINE.search(pagina), caminho
        assert not ATRIBUTO_INLINE.search(pagina), caminho


@pytest.mark.django_db
def test_paginas_publicas_enviam_permissions_policy(client: Client) -> None:
    for caminho, _status in _paginas_publicas():
        resposta = client.get(caminho)
        assert resposta["Permissions-Policy"] == PERMISSIONS_POLICY, caminho


def test_permissions_policy_da_propria_view_e_mantido(rf: RequestFactory) -> None:
    """Uma view que já defina o cabeçalho fica com o valor dela."""

    def view(request: HttpRequest) -> HttpResponse:
        resposta = HttpResponse()
        resposta["Permissions-Policy"] = "camera=(self)"
        return resposta

    resposta = PermissionsPolicyMiddleware(view)(rf.get("/"))

    assert resposta["Permissions-Policy"] == "camera=(self)"


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_login_do_admin_leva_o_nonce_no_estilo_e_nada_mais(client: Client) -> None:
    resposta = client.get(reverse("admin:login"))
    politica = _politica(resposta)
    assert politica["script-src"] == ["'self'"]
    nonce = politica["style-src"][1].removeprefix("'nonce-").removesuffix("'")
    assert nonce
    assert politica["style-src"] == ["'self'", f"'nonce-{nonce}'"]
    assert f'nonce="{nonce}"' in resposta.content.decode()
    assert resposta["Permissions-Policy"] == PERMISSIONS_POLICY


@pytest.mark.django_db
def test_inline_do_admin_sempre_traz_o_nonce_do_pedido(client: Client) -> None:
    """
    Todo nonce do Admin é o do pedido; script inline e ``<style>`` sem ele não há.

    Um bloqueado pela CSP quebraria a tela sem erro no servidor: só o console do
    navegador acusaria. O Admin põe o nonce nos ``<link>`` e nos ``<script src>``
    de cada página; a lista não pode vir vazia, senão a conferência não rodou.
    """
    receita = _receita()
    client.force_login(
        User.objects.create_user(
            username="admin-teste",
            password="senha-forte-123",
            is_staff=True,
            is_superuser=True,
        )
    )
    for caminho in [
        reverse("admin:index"),
        reverse("admin:receitas_receita_changelist"),
        reverse("admin:receitas_receita_add"),
        reverse("admin:receitas_receita_change", args=[receita.pk]),
        reverse("admin:receitas_receita_delete", args=[receita.pk]),
    ]:
        resposta = client.get(caminho)
        assert resposta.status_code == 200, caminho
        valores = _politica(resposta)["style-src"]
        nonce = valores[1].removeprefix("'nonce-").removesuffix("'")
        pagina = resposta.content.decode()
        nonces = NONCE.findall(pagina)
        assert nonces, caminho
        assert set(nonces) == {nonce}, caminho
        # O script-src não aceita nonce: script inline nenhum, nem no Admin.
        assert not SCRIPT_INLINE.search(pagina), caminho
        for tag in ESTILO_INLINE.findall(pagina):
            assert f'nonce="{nonce}"' in tag, (caminho, tag)
        assert not ATRIBUTO_INLINE.search(pagina), caminho
