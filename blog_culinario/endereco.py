"""
Endereço público do site: validação de ``URL_PUBLICA`` e endereços absolutos (spec 010).

``URL_PUBLICA`` é a única fonte do endereço absoluto no canonical, no
``og:url``, no ``robots.txt``, no ``sitemap.xml`` e no ``security.txt``. Nada
aqui lê o ``Host`` do pedido: o cabeçalho vem do cliente, e um endereço
canônico precisa ser um só (RNF-03 da spec 010).

O ``settings/base.py`` importa este módulo durante a carga das configurações,
então ele só importa ``urllib``, o ``settings`` preguiçoso do Django e
``django.core.exceptions`` (ADR-5 da spec 010): nada de views nem de models.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

_ESQUEMAS_ACEITOS = ("http", "https")


def normalizar_url_publica(valor: str) -> str:
    """
    Valida ``URL_PUBLICA`` e devolve só esquema e host, sem a barra final.

    Args:
        valor (str): valor lido do ambiente; vazio desliga o que depende dele.

    Returns:
        str: ``esquema://host[:porta]``, ou ``""`` para valor vazio.

    Raises:
        ImproperlyConfigured: se o valor não for só esquema ``http``/``https`` e
            host (sem caminho, query, fragmento, usuário ou senha).
    """
    valor = valor.strip()
    if not valor:
        return ""

    erro = ImproperlyConfigured(
        "URL_PUBLICA deve ser só esquema e host, como https://exemplo.com.br; "
        f"recebido: {valor!r}"
    )
    try:
        partes = urlsplit(valor)
        # .port levanta ValueError com porta fora do intervalo ou não numérica.
        _ = partes.port
    except ValueError as exc:
        raise erro from exc

    if (
        partes.scheme not in _ESQUEMAS_ACEITOS
        or not partes.hostname
        or partes.username is not None
        or partes.password is not None
        or partes.path not in ("", "/")
        or partes.query
        or partes.fragment
        or valor.endswith(("?", "#"))
    ):
        raise erro
    return f"{partes.scheme}://{partes.netloc}"


# ---------------------------------------------------------------------------
# Endereço absoluto
# ---------------------------------------------------------------------------


def url_absoluta(caminho: str) -> str:
    """
    Junta ``URL_PUBLICA`` a um caminho do site.

    Lê a setting na hora da chamada, para o ``override_settings`` dos testes
    valer.

    Args:
        caminho (str): caminho começando por ``/`` (saída de ``reverse`` ou de
            ``request.path``).

    Returns:
        str: o endereço absoluto, ou ``""`` sem ``URL_PUBLICA``.
    """
    url_publica: str = settings.URL_PUBLICA
    if not url_publica:
        return ""
    return f"{url_publica}{caminho}"
