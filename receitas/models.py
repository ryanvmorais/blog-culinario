"""
Domínio de receitas: Categoria, Tag, Receita (spec 001) e Comentario
(spec 005).

Só o modelo de dados e a geração de slug — views/templates públicos, busca
e moderação são escopo das specs seguintes (ver specs/README.md).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from .utils import gerar_slug_unico

# Limite de upload da imagem de capa (RF-04) — evita que uma foto de celular
# sem compressão vá parar direto em media/ sem controle de tamanho.
_TAMANHO_MAXIMO_IMAGEM = 5 * 1024 * 1024  # 5 MB


def validar_tamanho_imagem(arquivo: models.fields.files.FieldFile) -> None:
    """
    Rejeita arquivos de imagem acima de ``_TAMANHO_MAXIMO_IMAGEM``.

    Args:
        arquivo (FieldFile): arquivo enviado ao campo ``imagem_capa``.

    Returns:
        None

    Raises:
        django.core.exceptions.ValidationError: se ``arquivo.size`` exceder
            o limite de 5 MB.
    """
    if arquivo.size > _TAMANHO_MAXIMO_IMAGEM:
        raise ValidationError("A imagem deve ter no máximo 5 MB.")


class Categoria(models.Model):
    """
    Agrupamento temático de receitas (ex.: Sobremesas, Massas, Veganas).

    Attributes:
        nome (str): Nome de exibição, não único (RF-01) — duas categorias
            podem se chamar igual e ainda receber slugs distintos.
        slug (str): Slug gerado automaticamente a partir do ``nome`` no
            primeiro ``save()`` quando não fornecido; único no banco.
    """

    # unique fica no slug, não no nome (RF-01): duas categorias podem ter o
    # mesmo nome de exibição e ainda assim receber slugs distintos.
    nome = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categorias"
        ordering = ["nome"]

    def __str__(self) -> str:
        """
        Returns:
            str: o nome da categoria.
        """
        return self.nome

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Salva a categoria, gerando um slug único a partir do nome quando vazio.

        Args:
            *args (Any): argumentos posicionais repassados ao ``super().save()``
                (``force_insert``, ``force_update``, ...).
            **kwargs (Any): argumentos nomeados repassados ao ``super().save()``.

        Returns:
            None
        """
        if not self.slug:
            self.slug = gerar_slug_unico(Categoria, self.nome)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """
    Rótulo livre para filtrar receitas por característica (ex.: "sem glúten").

    Attributes:
        nome (str): Nome de exibição, não único — mesma razão de
            ``Categoria.nome`` (RF-02).
        slug (str): Slug gerado automaticamente a partir do ``nome`` no
            primeiro ``save()`` quando não fornecido; único no banco.
    """

    # unique fica no slug, não no nome — mesma razão de Categoria (RF-02).
    nome = models.CharField(max_length=40)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        """
        Returns:
            str: o nome da tag.
        """
        return self.nome

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Salva a tag, gerando um slug único a partir do nome quando vazio.

        Args:
            *args (Any): argumentos posicionais repassados ao ``super().save()``
                (``force_insert``, ``force_update``, ...).
            **kwargs (Any): argumentos nomeados repassados ao ``super().save()``.

        Returns:
            None
        """
        if not self.slug:
            self.slug = gerar_slug_unico(Tag, self.nome)
        super().save(*args, **kwargs)


class Receita(models.Model):
    """
    Uma receita publicável: ingredientes, modo de preparo e metadados.

    O slug é gerado automaticamente a partir do título no primeiro
    ``save()`` quando não fornecido.

    Attributes:
        titulo (str): Título da receita.
        slug (str): Slug único gerado a partir do ``titulo``.
        resumo (str): Resumo curto exibido no cartão da listagem.
        ingredientes (str): Lista de ingredientes em texto livre.
        modo_de_preparo (str): Passo a passo do preparo em texto livre.
        tempo_preparo_minutos (int): Tempo estimado de preparo, em minutos.
        porcoes (int): Número de porções que a receita rende.
        imagem_capa (ImageFieldFile): Imagem de capa opcional, validada por
            extensão (jpg/jpeg/png/webp) e tamanho máximo de 5 MB.
        categoria (Categoria): ``on_delete=PROTECT`` — não é permitido
            apagar uma categoria em uso (ADR-2 trata só do autor; aqui a
            regra é a oposta de propósito, ver spec 001 RF-03).
        tags (ManyRelatedManager): Tags associadas à receita, opcionais.
        autor (User | None): ``on_delete=SET_NULL`` — remover o usuário não
            apaga o conteúdo da receita (ADR-2).
        publicado (bool): controla se a receita pode aparecer nas views
            públicas (a view em si é escopo da spec seguinte).
        criado_em (datetime): Data/hora de criação (``auto_now_add``).
        atualizado_em (datetime): Data/hora da última atualização
            (``auto_now``).
    """

    titulo = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    resumo = models.CharField(max_length=280)
    ingredientes = models.TextField()
    modo_de_preparo = models.TextField()
    tempo_preparo_minutos = models.PositiveIntegerField()
    porcoes = models.PositiveSmallIntegerField()
    imagem_capa = models.ImageField(
        upload_to="receitas/capas/%Y/%m/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validar_tamanho_imagem,
        ],
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="receitas",
    )
    tags = models.ManyToManyField(Tag, related_name="receitas", blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receitas",
    )
    publicado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        """
        Returns:
            str: o título da receita.
        """
        return self.titulo

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Salva a receita, gerando um slug único a partir do título quando vazio.

        Args:
            *args (Any): argumentos posicionais repassados ao ``super().save()``
                (``force_insert``, ``force_update``, ...).
            **kwargs (Any): argumentos nomeados repassados ao ``super().save()``.

        Returns:
            None
        """
        if not self.slug:
            self.slug = gerar_slug_unico(Receita, self.titulo)
        super().save(*args, **kwargs)


class Comentario(models.Model):
    """
    Comentário de um usuário autenticado numa receita.

    Attributes:
        receita (Receita): ``on_delete=CASCADE`` — comentário não
            sobrevive sem a receita que comenta.
        autor (User | None): ``on_delete=SET_NULL`` — mesma política de
            ``Receita.autor`` (spec 001, ADR-2): preserva o comentário
            mesmo se o usuário for removido.
        texto (str): Conteúdo do comentário em texto livre.
        aprovado (bool): moderação reativa — nasce ``True``, o admin
            desmarca para esconder sem apagar (spec 005, ADR-4).
        criado_em (datetime): Data/hora de criação (``auto_now_add``).
    """

    receita = models.ForeignKey(
        Receita,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comentarios",
    )
    texto = models.TextField()
    aprovado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]  # conversa cronológica: mais antigo primeiro

    def __str__(self) -> str:
        """
        Returns:
            str: identificação curta do comentário (autor + receita).
        """
        return f"Comentário de {self.autor} em {self.receita}"
