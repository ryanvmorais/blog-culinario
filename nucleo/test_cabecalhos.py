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
from django.http import HttpResponseBase
from django.test import Client
from django.urls import reverse

from blog_culinario.cabecalhos import PERMISSIONS_POLICY
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

# Código que roda sem vir de um arquivo: <script> sem src, <style>, atributo
# style="" e atributo de evento (onclick="" etc.).
SCRIPT_INLINE = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>", re.IGNORECASE)
ESTILO_INLINE = re.compile(r"<style[^>]*>", re.IGNORECASE)
ATRIBUTO_INLINE = re.compile(r"\s(style|on[a-z]+)\s*=", re.IGNORECASE)


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
        assert "camera=()" in resposta["Permissions-Policy"]


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_login_do_admin_leva_o_nonce_no_estilo_e_nada_mais(client: Client) -> None:
    resposta = client.get(reverse("admin:login"))
    politica = _politica(resposta)
    assert politica["script-src"] == ["'self'"]
    assert politica["style-src"][0] == "'self'"
    nonce = politica["style-src"][1].removeprefix("'nonce-").removesuffix("'")
    assert f'nonce="{nonce}"' in resposta.content.decode()
    assert resposta["Permissions-Policy"] == PERMISSIONS_POLICY


@pytest.mark.django_db
def test_inline_do_admin_sempre_traz_o_nonce_do_pedido(client: Client) -> None:
    """
    Todo <style> inline do Admin traz o nonce, e script inline não há.

    Um bloqueado pela CSP quebraria a tela sem erro no servidor: só o console do
    navegador acusaria.
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
        # O script-src não aceita nonce: script inline nenhum, nem no Admin.
        assert not SCRIPT_INLINE.search(pagina), caminho
        for tag in ESTILO_INLINE.findall(pagina):
            assert f'nonce="{nonce}"' in tag, (caminho, tag)
        assert not ATRIBUTO_INLINE.search(pagina), caminho
