"""
Views institucionais: a home e a mídia enviada pelo Admin.

Ficam de fora do app ``receitas`` porque não pertencem ao domínio de
receitas — são as páginas e os arquivos que sustentam o site como um todo.
"""

from __future__ import annotations

import mimetypes

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe
from django.views.static import serve

from receitas.models import Categoria, Comentario, Receita

# O Python 3.12 só conhece o .webp pelo mime.types do sistema, que o contêiner
# da plataforma não tem (o tipo entrou no mimetypes no 3.13). Sem ele, a
# servir_midia responde application/octet-stream a toda capa convertida para
# WebP, com o nosniff ligado (spec 011, RF-07).
mimetypes.add_type("image/webp", ".webp")


def home(request: HttpRequest) -> HttpResponse:
    """
    Renderiza a página inicial: destaque, categorias, recentes e os números.

    Quatro consultas, quantas forem as receitas (spec 012, RNF-02): as 4
    publicadas mais recentes, o total de publicadas, as categorias com
    contagem e o total de comentários aprovados. O rodapé faz a quinta, pela
    tag ``{% categorias_do_rodape %}`` (ADR-3).

    Args:
        request (HttpRequest): requisição recebida.

    Returns:
        HttpResponse: ``nucleo/home.html`` renderizado.
    """
    publicadas = Receita.objects.filter(publicado=True)

    # Uma consulta só para o destaque e as recentes: as recentes nunca
    # repetem o destaque (spec 012, ADR-1). O select_related traz a categoria
    # de cada cartão no mesmo SELECT.
    ultimas = list(publicadas.select_related("categoria")[:4])
    destaque = ultimas[0] if ultimas else None

    # A lista avaliada aqui serve às pílulas e ao número de categorias, sem
    # uma segunda consulta (RF-03 e RF-06).
    categorias = list(Categoria.objects.com_receitas_publicadas())

    contexto = {
        "destaque": destaque,
        "recentes": ultimas[1:],
        "total_receitas": publicadas.count(),
        "categorias": categorias,
        "total_comentarios": Comentario.objects.filter(
            aprovado=True, receita__publicado=True
        ).count(),
    }
    return render(request, "nucleo/home.html", contexto)


@require_safe
@cache_control(public=True, max_age=86400)
def servir_midia(request: HttpRequest, caminho: str) -> HttpResponseBase:
    """
    Serve um arquivo de ``MEDIA_ROOT`` (as capas das receitas), com ou sem DEBUG.

    Na plataforma não há servidor web na frente para cuidar de ``/media/``, e o
    WhiteNoise só indexa arquivos quando o processo sobe, então uma capa nova
    só apareceria no reinício seguinte (spec 011, ADR-6). O ``serve`` do Django
    junta o caminho ao ``MEDIA_ROOT`` com ``safe_join``, recusa pasta com 404
    (sem listar arquivos), põe o ``Content-Type`` pela extensão e responde 304
    ao ``If-Modified-Since``. O ``Cache-Control`` de um dia não esconde troca de
    capa: o Django dá nome novo ao arquivo quando o nome já existe.

    Args:
        request (HttpRequest): requisição recebida (GET ou HEAD).
        caminho (str): caminho do arquivo dentro de ``MEDIA_ROOT``, vindo da URL.

    Returns:
        HttpResponseBase: o arquivo, ou 304 se o navegador já tem a versão atual.

    Raises:
        Http404: se o arquivo não existe, é uma pasta ou sai de ``MEDIA_ROOT``.
    """
    try:
        return serve(request, caminho, document_root=settings.MEDIA_ROOT)
    except SuspiciousFileOperation as erro:
        # O ../ que sai da pasta viraria 400 e uma linha de log; responde como
        # um arquivo que não existe.
        raise Http404 from erro
