"""
Sitemap das receitas publicadas (spec 010, RF-05).

Cada receita publicada entra com o endereço do detalhe e o ``lastmod`` do
``atualizado_em``. Domínio e protocolo vêm de ``URL_PUBLICA``, pela classe base
``SitemapPublico`` (ADR-1 da spec 010).
"""

from __future__ import annotations

from datetime import datetime

from django.db.models import QuerySet
from django.urls import reverse

from blog_culinario.descoberta import SitemapPublico

from .models import Receita


class ReceitaSitemap(SitemapPublico):
    """Uma entrada por receita publicada."""

    def items(self) -> QuerySet[Receita]:
        """
        Receitas que as views públicas mostram.

        A ordem vem do ``Meta.ordering`` do model, e por isso o paginador do
        sitemap não avisa de lista sem ordem.

        Returns:
            QuerySet[Receita]: receitas com ``publicado=True``.
        """
        return Receita.objects.filter(publicado=True)

    def location(self, item: Receita) -> str:
        """
        Caminho do detalhe da receita, igual ao do canonical da página.

        Args:
            item (Receita): receita publicada.

        Returns:
            str: o caminho do detalhe.
        """
        return reverse("receitas:detalhe", kwargs={"slug": item.slug})

    def lastmod(self, item: Receita) -> datetime:
        """
        Última atualização da receita.

        Args:
            item (Receita): receita publicada.

        Returns:
            datetime: o ``atualizado_em``; o template do Django escreve só a data.
        """
        return item.atualizado_em
