"""
Trava de origem e IP do visitante atrás da Cloudflare (spec 011).

Atrás de um proxy, o ``REMOTE_ADDR`` é o endereço do proxy, não o do visitante,
e a limitação de taxa (spec 006) dividiria um contador só entre todo mundo. A
Cloudflare manda o IP real no ``CF-Connecting-IP``, mas um cliente que alcance
o serviço por outro caminho pode inventar esse cabeçalho. A trava resolve: uma
regra de transformação da Cloudflare acrescenta a todo pedido o cabeçalho
``X-Origin-Verify`` com um segredo, sobrescrevendo o que o visitante enviar, e
o middleware daqui recusa o pedido que não o traz. Com a trava ligada, o pedido
que chega às views passou pela Cloudflare, e o ``CF-Connecting-IP`` é confiável.

A trava é opcional (spec 011, ADR-5): sem ``ORIGEM_SEGREDO``, o middleware não
faz nada e o IP é o ``REMOTE_ADDR``, para quem publica sem Cloudflare.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Chaves do request.META: o Django põe cada cabeçalho em maiúsculas, com o
# prefixo HTTP_ e "_" no lugar de "-".
CABECALHO_ORIGEM = "HTTP_X_ORIGIN_VERIFY"
CABECALHO_IP = "HTTP_CF_CONNECTING_IP"


# ---------------------------------------------------------------------------
# Trava de origem
# ---------------------------------------------------------------------------


def trava_de_origem_ligada() -> bool:
    """
    Diz se há segredo de origem configurado.

    Lido a cada chamada, e não guardado na importação: a troca de segredo e o
    ``override_settings`` dos testes valem na hora.

    Returns:
        bool: ``True`` se ``ORIGEM_SEGREDO`` (ou o anterior) está definida.
    """
    return bool(settings.ORIGEM_SEGREDOS)


def _veio_pelo_proxy(request: HttpRequest, segredos: tuple[str, ...]) -> bool:
    """
    Confere o cabeçalho de origem contra os segredos aceitos.

    Args:
        request (HttpRequest): pedido recebido.
        segredos (tuple[str, ...]): segredos aceitos (o atual e, durante a
            troca, o anterior).

    Returns:
        bool: ``True`` se o cabeçalho é igual a algum segredo. A comparação é em
        tempo constante (``hmac.compare_digest``), para o tempo de resposta não
        revelar quantos caracteres do palpite estavam certos (RNF-05); todos os
        segredos são comparados, mesmo depois de um acerto.
    """
    recebido = request.META.get(CABECALHO_ORIGEM, "").encode()
    acertos = [hmac.compare_digest(recebido, s.encode()) for s in segredos]
    return any(acertos)


class OrigemCloudflareMiddleware:
    """
    Recusa com 403 o pedido sem o segredo de origem, quando a trava está ligada.

    Fica no topo do ``MIDDLEWARE``: o que não veio pelo proxy não chega a
    nenhuma outra camada, nem ao redirect de HTTPS (RF-09).

    Attributes:
        get_response (Callable[[HttpRequest], HttpResponseBase]): a próxima
            camada da pilha de middlewares.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        """
        Guarda a próxima camada da pilha.

        Args:
            get_response (Callable[[HttpRequest], HttpResponseBase]): a próxima
                camada, que o Django passa ao montar a pilha.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Deixa passar o pedido com o segredo, ou todos com a trava desligada.

        Args:
            request (HttpRequest): pedido recebido.

        Returns:
            HttpResponseBase: a resposta da próxima camada.

        Raises:
            PermissionDenied: se a trava está ligada e o cabeçalho falta ou não
                bate. O Django converte a exceção na página ``403.html``.
        """
        segredos: tuple[str, ...] = settings.ORIGEM_SEGREDOS
        if segredos and not _veio_pelo_proxy(request, segredos):
            # O valor recebido nunca vai para o log, só o método e o caminho.
            logger.warning(
                "pedido sem o segredo de origem: %s %s", request.method, request.path
            )
            raise PermissionDenied
        return self.get_response(request)


# ---------------------------------------------------------------------------
# IP do visitante
# ---------------------------------------------------------------------------


def ip_do_visitante(request: HttpRequest) -> str:
    """
    Devolve o IP de quem fez o pedido, para a limitação de taxa.

    Com a trava ligada, o middleware já garantiu que o pedido passou pela
    Cloudflare, que sobrescreve o ``CF-Connecting-IP`` a cada pedido (RF-10).
    Sem a trava, o cabeçalho pode ter vindo do cliente e é ignorado.

    Args:
        request (HttpRequest): pedido recebido.

    Returns:
        str: o ``CF-Connecting-IP``, se a trava está ligada e ele é um endereço
        válido; senão, o ``REMOTE_ADDR`` (``"desconhecido"`` se faltar).
    """
    remoto: str = request.META.get("REMOTE_ADDR", "desconhecido")
    if not trava_de_origem_ligada():
        return remoto
    candidato = request.META.get(CABECALHO_IP, "").strip()
    try:
        return str(ipaddress.ip_address(candidato))
    except ValueError:
        return remoto
