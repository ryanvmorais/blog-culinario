"""
Limitação de taxa simples baseada no cache do Django (spec 006).

Sem dependência nova (RNF-01): usa o cache do Django para contar tentativas
por IP numa janela de tempo. O cache é em arquivo, compartilhado entre os
workers do gunicorn, com ``add()`` e ``incr()`` atômicos
(``blog_culinario/cache.py``, spec 011). Compartilhado entre ``usuarios``
(login) e ``receitas`` (comentário) — por isso vive aqui, no pacote do
projeto, e não dentro de um app de domínio (ADR-1 da spec 006).
"""

from __future__ import annotations

from django.core.cache import cache
from django.http import HttpRequest

from blog_culinario.origem import ip_do_visitante

_PREFIXO_CACHE = "limite"


def limite_excedido(
    request: HttpRequest, chave: str, limite: int, janela_segundos: int
) -> bool:
    """
    Verifica se o IP da requisição excedeu o limite de tentativas na janela.

    Incrementa o contador como efeito colateral — chamar esta função já
    conta como uma tentativa, então cada view chama exatamente uma vez por
    requisição (RF-01, RF-02). A tentativa recusada também soma, sem efeito
    visível: o contador não estende a janela, e a recusa dura até ela acabar.

    Args:
        request (HttpRequest): requisição atual; o identificador é o IP do
            visitante (``ip_do_visitante``: o ``CF-Connecting-IP`` com a trava
            de origem ligada, senão o ``REMOTE_ADDR``, spec 011), não o usuário
            autenticado (RNF-02, ADR-3).
        chave (str): namespace do limite (ex.: ``"login"``, ``"comentario"``)
            — evita que login e comentário compartilhem o mesmo contador.
        limite (int): número máximo de tentativas permitidas na janela.
        janela_segundos (int): duração da janela, em segundos; o contador
            expira sozinho no cache ao final dela (RF-03).

    Returns:
        bool: True se o limite já foi atingido (a tentativa atual deve ser
        rejeitada); False se a tentativa foi contabilizada normalmente.
    """
    ip = ip_do_visitante(request)
    cache_key = f"{_PREFIXO_CACHE}:{chave}:{ip}"

    # add() só cria o contador se ele ainda não existir, e o incr() mantém a
    # validade dele: a janela começa na primeira tentativa e não reinicia. Cada
    # pedido recebe do incr() atômico um número só seu, então no máximo
    # `limite` pedidos passam na janela, mesmo chegando juntos (spec 011, RF-08).
    cache.add(cache_key, 0, timeout=janela_segundos)
    try:
        tentativas = cache.incr(cache_key)
    except ValueError:  # o contador expirou entre o add() e o incr()
        cache.add(cache_key, 0, timeout=janela_segundos)
        tentativas = cache.incr(cache_key)
    return tentativas > limite
