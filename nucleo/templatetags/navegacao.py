"""
Tags de navegação: links para o código no repositório e as categorias do rodapé.

``{% link_repositorio %}`` monta o endereço de um arquivo ou de uma pasta do
projeto no GitHub, a partir do ``URL_REPOSITORIO`` que o modo demonstração já
usa (spec 012, ADR-8). ``{% categorias_do_rodape %}`` é uma inclusion tag: só
consulta o banco quando o rodapé é desenhado, e as páginas de erro, que têm
rodapé próprio, continuam sem tocar no banco (spec 012, ADR-3).

Uso::

    {% load navegacao %}
    <a href="{% link_repositorio 'nucleo/views.py' %}">nucleo/views.py</a>
    {% categorias_do_rodape %}
"""

from __future__ import annotations

from django import template

from blog_culinario.demonstracao import URL_REPOSITORIO
from receitas.models import Categoria

register = template.Library()

# Os links apontam para a branch principal: a nota descreve o código atual,
# não um commit fixo (spec 012, ADR-8).
_BRANCH = "main"


# ---------------------------------------------------------------------------
# Links para o repositório
# ---------------------------------------------------------------------------


@register.simple_tag
def link_repositorio(caminho: str) -> str:
    """
    Endereço de um arquivo ou de uma pasta do projeto no GitHub.

    Args:
        caminho (str): caminho a partir da raiz do repositório; termina em
            ``/`` quando é uma pasta (``"specs/"``).

    Returns:
        str: ``.../blob/main/<caminho>`` para arquivo ou
            ``.../tree/main/<caminho>`` para pasta, sem a barra final.
    """
    tipo = "tree" if caminho.endswith("/") else "blob"
    return f"{URL_REPOSITORIO}/{tipo}/{_BRANCH}/{caminho.rstrip('/')}"


# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------


@register.inclusion_tag("includes/rodape_categorias.html")
def categorias_do_rodape() -> dict[str, list[Categoria]]:
    """
    Categorias com receita publicada, para a coluna "Categorias" do rodapé.

    Returns:
        dict[str, list[Categoria]]: ``{"categorias": [...]}`` na ordem de
            ``Categoria.objects.com_receitas_publicadas()`` (spec 012, RF-12).
    """
    return {"categorias": list(Categoria.objects.com_receitas_publicadas())}
