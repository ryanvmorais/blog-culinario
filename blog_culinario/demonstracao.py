"""
Modo demonstração: o que a instância pública mostra e deixa de gravar (spec 009).

Com ``MODO_DEMONSTRACAO`` ligado, cadastro e comentário continuam validando,
mas não gravam nada e respondem com uma mensagem que aponta o repositório. O
login segue funcionando com uma conta pública, cujas credenciais aparecem na
tela de login. Este módulo concentra as constantes, os textos e o context
processor; quem decide se grava são as próprias views (ADR-1 da spec 009).
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Públicas de propósito: aparecem na tela de login. Ficam no código, não numa
# variável de ambiente, para a tela mostrar exatamente a senha que o comando
# criar_conta_demonstracao grava (ADR-5 da spec 009).
USUARIO_DEMONSTRACAO = "visitante"
SENHA_DEMONSTRACAO = "receitas-demo"

URL_REPOSITORIO = "https://github.com/ryanvmorais/blog-culinario"


# ---------------------------------------------------------------------------
# Estado do modo
# ---------------------------------------------------------------------------


def modo_demonstracao_ligado() -> bool:
    """
    Diz se a instância está em modo demonstração.

    Lê a setting na hora da chamada, não na importação do módulo, para o
    ``override_settings`` dos testes valer.

    Returns:
        bool: True se ``MODO_DEMONSTRACAO`` está ligado.
    """
    return bool(settings.MODO_DEMONSTRACAO)


# ---------------------------------------------------------------------------
# Mensagens depois do envio
# ---------------------------------------------------------------------------


def _link_repositorio(texto: str) -> SafeString:
    """
    Monta o link para o repositório, aberto numa aba nova como o do rodapé.

    Args:
        texto (str): texto visível do link.

    Returns:
        SafeString: o ``<a>`` pronto, com o texto escapado.
    """
    return format_html(
        '<a href="{}" target="_blank" rel="noopener">{}</a>', URL_REPOSITORIO, texto
    )


def mensagem_cadastro() -> SafeString:
    """
    Texto mostrado quando um cadastro válido é recusado pelo modo (RF-03).

    ``SafeString`` para o link sair como HTML: o armazenamento de mensagens do
    Django preserva a marca entre o POST e o GET (ADR-2 da spec 009). Só
    interpola constantes, nunca dado do visitante.

    Returns:
        SafeString: a mensagem com o link para o repositório.
    """
    return format_html(
        "Este blog é um projeto educacional e não cria contas. Para ver como o "
        "cadastro funciona, {}. Para comentar, entre com a conta de demonstração.",
        _link_repositorio("clone ou baixe o código no GitHub"),
    )


def mensagem_comentario() -> SafeString:
    """
    Texto mostrado quando um comentário é recusado pelo modo (RF-06).

    Returns:
        SafeString: a mensagem com o link para o repositório (ver
        ``mensagem_cadastro`` sobre o ``SafeString``).
    """
    return format_html(
        "Este blog é um projeto educacional e não publica comentários. Para ver "
        "como funciona, {}.",
        _link_repositorio("clone ou baixe o código no GitHub"),
    )


# ---------------------------------------------------------------------------
# Context processor
# ---------------------------------------------------------------------------


def contexto_demonstracao(request: HttpRequest) -> dict[str, object]:
    """
    Entrega aos templates o estado do modo e, ligado, a conta pública (ADR-3).

    As credenciais só entram no contexto com o modo ligado, para nenhum
    template as mostrar por engano numa instância comum.

    Args:
        request (HttpRequest): requisição atual (exigida pela assinatura de
            context processor; não é usada).

    Returns:
        dict[str, object]: ``modo_demonstracao`` sempre e
        ``conta_demonstracao`` (``usuario`` e ``senha``) só com o modo ligado.
    """
    if not modo_demonstracao_ligado():
        return {"modo_demonstracao": False}
    return {
        "modo_demonstracao": True,
        "conta_demonstracao": {
            "usuario": USUARIO_DEMONSTRACAO,
            "senha": SENHA_DEMONSTRACAO,
        },
    }
