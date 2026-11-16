"""
Middleware do cabeçalho ``Permissions-Policy`` (spec 011, RF-17).

O cabeçalho diz ao navegador quais recursos do aparelho a página (e o que ela
embutir) pode pedir. O blog não usa nenhum, então todos ficam negados: um script
injetado não consegue nem pedir a câmera. O Django não tem configuração para
este cabeçalho, daí o middleware; a Content-Security-Policy vem do próprio
Django (``SECURE_CSP`` no ``settings/base.py``).
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase

# ---------------------------------------------------------------------------
# Política
# ---------------------------------------------------------------------------

# Só nomes que o Chrome reconhece: um nome desconhecido vira erro no console do
# navegador, e o Lighthouse desconta erro de console.
PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class PermissionsPolicyMiddleware:
    """
    Acrescenta o cabeçalho ``Permissions-Policy`` a toda resposta.

    Uma view que já defina o cabeçalho mantém o valor dela.

    Attributes:
        get_response (Callable[[HttpRequest], HttpResponseBase]): Próxima
            camada da cadeia de middlewares.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        """
        Guarda a próxima camada da cadeia.

        Args:
            get_response (Callable[[HttpRequest], HttpResponseBase]): Próxima
                camada da cadeia de middlewares.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Repassa o pedido e acrescenta o cabeçalho à resposta.

        Args:
            request (HttpRequest): Pedido recebido.

        Returns:
            HttpResponseBase: A resposta da cadeia, com o cabeçalho.
        """
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
