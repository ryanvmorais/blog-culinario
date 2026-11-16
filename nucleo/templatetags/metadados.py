"""
Tag ``{% capturar %}``: o texto de um bloco usado em mais de um lugar (spec 010).

A linguagem de templates do Django não renderiza o mesmo ``{% block %}`` duas
vezes. O ``base.html`` precisa do título da página no ``<title>`` e no
``og:title``, e da descrição na ``description`` e no ``og:description``; com
esta tag ele guarda o que o bloco renderizou numa variável e a usa onde
quiser, sem que os templates filhos mudem (ADR-2 da spec 010).

Uso::

    {% load metadados %}
    {% capturar titulo_pagina %}{% block titulo %}Padrão{% endblock %}{% endcapturar %}
    <title>{{ titulo_pagina }}</title>
"""

from __future__ import annotations

from django import template
from django.template.base import NodeList, Parser, Token
from django.template.context import Context
from django.utils.safestring import mark_safe

register = template.Library()


class NoCaptura(template.Node):
    """
    Renderiza o conteúdo e o guarda no contexto, sem escrever nada no lugar.

    ``child_nodelists`` é o que deixa o ``{% extends %}`` achar os
    ``{% block %}`` de dentro: sem ele, os filhos não conseguiriam sobrescrever
    o bloco capturado.

    Attributes:
        nodelist (NodeList): conteúdo entre ``capturar`` e ``endcapturar``.
        nome (str): variável do contexto que recebe o texto renderizado.
    """

    child_nodelists = ("nodelist",)

    def __init__(self, nodelist: NodeList, nome: str) -> None:
        """
        Guarda o conteúdo e o nome da variável.

        Args:
            nodelist (NodeList): conteúdo entre as duas tags.
            nome (str): variável do contexto que recebe o texto.
        """
        self.nodelist = nodelist
        self.nome = nome

    def render(self, context: Context) -> str:
        """
        Guarda o conteúdo renderizado em ``context[nome]``.

        O conteúdo já saiu escapado pelo autoescape de cada variável dentro
        dele; marcá-lo como seguro evita escapar duas vezes onde a variável
        for usada.

        Args:
            context (Context): contexto do template.

        Returns:
            str: sempre vazio; a tag não escreve nada no lugar.
        """
        context[self.nome] = mark_safe(self.nodelist.render(context).strip())
        return ""


@register.tag
def capturar(parser: Parser, token: Token) -> NoCaptura:
    """
    Compila ``{% capturar nome %}…{% endcapturar %}``.

    Args:
        parser (Parser): parser do template.
        token (Token): a tag de abertura.

    Returns:
        NoCaptura: o nó que guarda o conteúdo no contexto.

    Raises:
        TemplateSyntaxError: se a tag não tiver exatamente um nome de variável.
    """
    partes = token.split_contents()
    if len(partes) != 2:
        raise template.TemplateSyntaxError(
            f"{partes[0]!r} recebe só o nome da variável: {{% capturar nome %}}"
        )
    nodelist = parser.parse(("endcapturar",))
    parser.delete_first_token()
    return NoCaptura(nodelist, partes[1])
