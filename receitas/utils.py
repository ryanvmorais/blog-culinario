"""
Geração de slug único, compartilhada pelos models de Categoria, Tag e
Receita (spec 001, ADR-1).

Vive fora dos models para não repetir a lógica de unicidade em cada
``save()`` — cada model só chama ``gerar_slug_unico`` quando o campo slug
está vazio.
"""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify


def gerar_slug_unico(
    modelo: type[models.Model],
    texto: str,
    campo_slug: str = "slug",
) -> str:
    """
    Gera um slug único para ``modelo``, resolvendo colisão com sufixo numérico.

    Args:
        modelo (type[models.Model]): classe do model onde a unicidade do
            slug é verificada (ex.: ``Categoria``, ``Receita``).
        texto (str): texto de origem (nome ou título) usado para gerar o
            slug base.
        campo_slug (str, optional): nome do campo slug no model. Padrão:
            ``"slug"``.

    Returns:
        str: slug único, ainda não usado por nenhuma instância de
        ``modelo`` (ex.: ``"bolo-de-cenoura"``, ou ``"bolo-de-cenoura-2"``
        se o primeiro já existir).
    """
    slug_base = slugify(texto)
    slug = slug_base
    contador = 2
    # django-stubs não infere `.objects` num `type[Model]` genérico — a
    # função aceita qualquer model de propósito (Categoria, Tag, Receita).
    while modelo.objects.filter(**{campo_slug: slug}).exists():  # type: ignore[attr-defined]
        slug = f"{slug_base}-{contador}"
        contador += 1
    return slug
