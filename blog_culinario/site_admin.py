"""
Site do Admin com limite de tentativas no login (spec 006, adendo, RF-04).

A tela de login do Admin é uma view do próprio ``AdminSite``, separada da
``EntrarView`` de ``usuarios``, e não passava pela limitação de taxa. Aqui o
site do Admin vira uma subclasse que conta cada POST de login no mesmo
contador do login público, antes de conferir usuário e senha.

A subclasse entra pelo ``default_site`` de um ``AdminConfig`` (ADR-5), o
caminho que a documentação do Django indica para trocar o site padrão: o
``admin.site`` de todo o projeto passa a ser este, e cada ``@admin.register``
dos apps continua igual. O ``INSTALLED_APPS`` lista ``ConfigAdmin`` no lugar
de ``django.contrib.admin``.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.contrib.admin.apps import AdminConfig
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from blog_culinario.limitacao import (
    JANELA_LOGIN_SEGUNDOS,
    LIMITE_LOGIN,
    MENSAGEM_LIMITE_LOGIN,
    limite_excedido,
)

# ---------------------------------------------------------------------------
# Site do Admin
# ---------------------------------------------------------------------------


class SiteAdminComLimite(admin.AdminSite):
    """O ``AdminSite`` do Django, com o login limitado por rede do visitante."""

    def login(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        """
        Recusa o POST de login acima do limite; o resto segue o Django.

        O contador é o ``"login"``, o mesmo da ``EntrarView`` (decisão
        resolvida 2 do adendo): esgotado numa tela, vale na outra. A visita por
        GET não conta.

        Args:
            request (HttpRequest): requisição recebida.
            extra_context (dict[str, Any] | None): contexto extra do template,
                repassado ao ``login()`` do Django.

        Returns:
            HttpResponse: acima do limite, redireciona para a mesma URL (o
            ``?next=`` incluso), com a mensagem de erro; senão, a resposta do
            ``login()`` do Django (RNF-05).
        """
        if request.method == "POST" and limite_excedido(
            request,
            "login",
            limite=LIMITE_LOGIN,
            janela_segundos=JANELA_LOGIN_SEGUNDOS,
        ):
            messages.error(request, MENSAGEM_LIMITE_LOGIN)
            return redirect(request.get_full_path())
        return super().login(request, extra_context)


# ---------------------------------------------------------------------------
# Configuração do app
# ---------------------------------------------------------------------------


class ConfigAdmin(AdminConfig):
    """O app do Admin do Django, com o ``SiteAdminComLimite`` como site padrão."""

    default_site = "blog_culinario.site_admin.SiteAdminComLimite"
