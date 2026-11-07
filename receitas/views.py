"""
Views públicas de receitas: listagem paginada com busca/filtros, detalhe
(specs 002 e 003) e criação de comentário (spec 005).

Class-based views de propósito (ADR-1 da spec 002) — em contraste com as
views baseadas em função de ``nucleo``, para o repositório mostrar os dois
estilos lado a lado.
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from blog_culinario.limitacao import limite_excedido

from .forms import (
    FormularioComentario,
    eh_envio_suspeito_de_bot,
    gerar_carimbo_de_tempo,
)
from .models import Categoria, Receita, Tag


def _nome_do_filtro(modelo: type[Categoria] | type[Tag], slug: str) -> str:
    """
    Devolve o nome de exibição de uma categoria ou tag a partir do slug.

    Args:
        modelo (type[Categoria] | type[Tag]): modelo com ``slug`` e ``nome``.
        slug (str): slug vindo da querystring; vazio significa "sem filtro".

    Returns:
        str: o ``nome`` do registro, ou ``""`` se não há slug ou ele não existe.
    """
    if not slug:
        return ""
    return modelo.objects.filter(slug=slug).values_list("nome", flat=True).first() or ""


class ReceitaListView(ListView):
    """
    Lista as receitas publicadas, 9 por página, mais recentes primeiro.

    Aceita três parâmetros GET opcionais e combináveis (spec 003, ADR-1):
    ``q`` (busca em título/ingredientes), ``categoria`` e ``tag`` (slugs).
    """

    model = Receita
    template_name = "receitas/lista.html"
    context_object_name = "receitas"
    paginate_by = 9

    def get_queryset(self) -> QuerySet[Receita]:
        """
        Restringe a listagem a receitas publicadas, filtradas e sem N+1.

        Returns:
            QuerySet[Receita]: receitas com ``publicado=True``, com
            categoria/autor pré-carregados via ``select_related``, tags via
            ``prefetch_related``, e os filtros de busca/categoria/tag da
            querystring aplicados (RF-01 a RF-04, RNF-01, RNF-02).
        """
        queryset = (
            Receita.objects.filter(publicado=True)
            .select_related("categoria", "autor")
            .prefetch_related("tags")
        )

        termo = self.request.GET.get("q", "").strip()
        if termo:
            queryset = queryset.filter(
                Q(titulo__icontains=termo) | Q(ingredientes__icontains=termo)
            )

        categoria_slug = self.request.GET.get("categoria", "").strip()
        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)

        tag_slug = self.request.GET.get("tag", "").strip()
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Expõe os filtros ativos e a querystring sem ``page`` (RF-06, RF-07, ADR-3).

        Args:
            **kwargs (Any): argumentos repassados ao ``super().get_context_data()``.

        Returns:
            dict[str, Any]: contexto do template, com ``termo_busca``,
            ``categoria_selecionada``, ``tag_selecionada`` (ecoam a
            querystring atual), ``categoria_nome`` e ``tag_nome`` (o nome
            de exibição do filtro, para a frase "N receitas em X"; vazios
            quando o slug não existe ou não há filtro), ``filtro_ativo``
            (``True`` se há busca, categoria ou tag) e ``querystring``
            (GET sem ``page``, urlencoded, usada pela paginação para
            preservar o filtro).
        """
        contexto = super().get_context_data(**kwargs)

        parametros = self.request.GET.copy()
        parametros.pop("page", None)

        contexto["termo_busca"] = self.request.GET.get("q", "")
        contexto["categoria_selecionada"] = self.request.GET.get("categoria", "")
        contexto["tag_selecionada"] = self.request.GET.get("tag", "")
        contexto["querystring"] = parametros.urlencode()
        # Só consulta o nome quando há filtro; sem filtro a listagem continua
        # em 3 queries (RNF-01 da spec 002).
        contexto["categoria_nome"] = _nome_do_filtro(
            Categoria, contexto["categoria_selecionada"]
        )
        contexto["tag_nome"] = _nome_do_filtro(Tag, contexto["tag_selecionada"])
        contexto["filtro_ativo"] = bool(
            contexto["termo_busca"]
            or contexto["categoria_selecionada"]
            or contexto["tag_selecionada"]
        )
        return contexto


class ReceitaDetailView(DetailView):
    """
    Exibe uma receita publicada pelo slug.

    O comportamento padrão do ``DetailView`` já cobre RF-04: como a
    queryset só contém receitas publicadas, um slug de rascunho ou
    inexistente resulta em 404 sem código extra.
    """

    model = Receita
    template_name = "receitas/detalhe.html"
    context_object_name = "receita"

    def get_queryset(self) -> QuerySet[Receita]:
        """
        Restringe o detalhe a receitas publicadas, sem N+1 (RNF-01).

        Returns:
            QuerySet[Receita]: receitas com ``publicado=True``, com
            categoria/autor/tags pré-carregados.
        """
        return (
            Receita.objects.filter(publicado=True)
            .select_related("categoria", "autor")
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Acrescenta os comentários aprovados e o formulário de novo comentário.

        Args:
            **kwargs (Any): argumentos repassados ao ``super().get_context_data()``.

        Returns:
            dict[str, Any]: contexto do template, com ``comentarios``
            (aprovados, mais antigo primeiro, autor pré-carregado — spec
            005 RF-02, RNF-01) e ``formulario_comentario`` (vazio; só é
            usado no template quando o visitante está autenticado).
        """
        contexto = super().get_context_data(**kwargs)
        comentarios = self.object.comentarios.filter(aprovado=True)
        contexto["comentarios"] = comentarios.select_related("autor")
        # carimbo_tempo nasce aqui, no momento em que a página é servida --
        # o time-trap da spec 007 (RF-02) compara com o instante do POST.
        contexto["formulario_comentario"] = FormularioComentario(
            initial={"carimbo_tempo": gerar_carimbo_de_tempo()}
        )
        return contexto


class ComentarioCreateView(LoginRequiredMixin, View):
    """
    Cria um comentário numa receita publicada; só aceita POST.

    O formulário vive embutido em ``receitas/detalhe.html`` (spec 005) —
    não existe uma página própria para esta view, então ela nunca
    responde a GET.
    """

    http_method_names = ["post"]

    def handle_no_permission(self) -> HttpResponseRedirect:
        """
        Redireciona ao login com ``next`` apontando para a receita (ADR-2).

        O padrão do ``LoginRequiredMixin`` usaria a URL desta própria view
        como ``next`` — mas ela só aceita POST, então o ``GET`` que o
        navegador faz após o login bateria num 405. Aponta direto para a
        página da receita, que é aonde o usuário queria chegar.

        Returns:
            HttpResponseRedirect: redirecionamento para ``usuarios:entrar``.
        """
        url_receita = reverse("receitas:detalhe", kwargs={"slug": self.kwargs["slug"]})
        return redirect_to_login(
            url_receita, self.get_login_url(), self.get_redirect_field_name()
        )

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        """
        Valida e salva o comentário, ou volta com uma mensagem de erro (ADR-3).

        Também bloqueia o IP que já atingiu o limite de comentários na
        janela de tempo (spec 006, RF-02) e filtra bots via honeypot/
        time-trap (spec 007) — nessa ordem, antes de qualquer acesso ao
        banco. Um envio pego pelo honeypot/time-trap finge sucesso sem
        salvar nada e sem consumir o limite de taxa (spec 007, ADR-3, ADR-4).

        Args:
            request (HttpRequest): requisição POST recebida, já autenticada.
            slug (str): slug da receita comentada, vindo da URL.

        Returns:
            HttpResponse: redireciona de volta para ``receitas:detalhe``,
            na âncora ``#comentarios``.
        """
        url_receita = reverse("receitas:detalhe", kwargs={"slug": slug})
        url_retorno = f"{url_receita}#comentarios"

        if eh_envio_suspeito_de_bot(request.POST):
            messages.success(request, "Comentário publicado!")
            return redirect(url_retorno)

        if limite_excedido(request, "comentario", limite=5, janela_segundos=60):
            messages.error(
                request, "Você está comentando rápido demais. Aguarde um instante."
            )
            return redirect(url_retorno)

        receita = get_object_or_404(Receita, slug=slug, publicado=True)
        form = FormularioComentario(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.receita = receita
            comentario.autor = request.user
            comentario.save()
            messages.success(request, "Comentário publicado!")
        else:
            messages.error(request, "O comentário não pode ficar vazio.")
        return redirect(url_retorno)
