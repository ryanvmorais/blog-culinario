"""Admin do domínio de receitas (spec 001, RF-05; spec 005, RF-07)."""

from __future__ import annotations

from django.contrib import admin
from django.utils.text import Truncator

from .models import Categoria, Comentario, Receita, Tag


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Listagem e formulário de categorias, com slug preenchido pelo nome."""

    list_display = ["nome", "slug"]
    search_fields = ["nome"]
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Listagem e formulário de tags, com slug preenchido pelo nome."""

    list_display = ["nome", "slug"]
    search_fields = ["nome"]
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    """
    Listagem e formulário de receitas.

    ``autocomplete_fields`` + ``list_select_related`` evitam que a listagem
    dispare uma query de categoria/autor por linha à medida que o volume de
    receitas cresce (RNF-02).
    """

    list_display = ["titulo", "categoria", "autor", "publicado", "criado_em"]
    list_filter = ["categoria", "publicado"]
    search_fields = ["titulo"]
    prepopulated_fields = {"slug": ("titulo",)}
    autocomplete_fields = ["categoria", "autor"]
    list_select_related = ["categoria", "autor"]


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """
    Moderação de comentários: aprovar/reprovar sem precisar apagar.

    ``list_editable`` deixa alternar ``aprovado`` direto na listagem — a
    forma mais rápida de moderar em volume (spec 005, RF-07).
    """

    list_display = ["texto_curto", "receita", "autor", "aprovado", "criado_em"]
    list_editable = ["aprovado"]
    list_filter = ["aprovado"]
    search_fields = ["texto"]
    autocomplete_fields = ["receita", "autor"]
    list_select_related = ["receita", "autor"]

    @admin.display(description="Comentário")
    def texto_curto(self, obj: Comentario) -> str:
        """
        Trunca o texto do comentário para caber na coluna da listagem.

        Args:
            obj (Comentario): a linha sendo renderizada.

        Returns:
            str: os primeiros ~60 caracteres do texto, com reticências se
            for maior.
        """
        return Truncator(obj.texto).chars(60)
