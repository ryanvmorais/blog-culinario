"""
Limitação de taxa simples baseada no cache do Django (spec 006).

Sem dependência nova (RNF-01): usa o backend de cache padrão (LocMemCache
quando ``CACHES`` não é configurado) para contar tentativas por IP numa
janela de tempo. Compartilhado entre ``usuarios`` (login) e ``receitas``
(comentário) — por isso vive aqui, no pacote do projeto, e não dentro de um
app de domínio (ADR-1 da spec 006).
"""

from __future__ import annotations

from django.core.cache import cache
from django.http import HttpRequest

_PREFIXO_CACHE = "limite"


def limite_excedido(
    request: HttpRequest, chave: str, limite: int, janela_segundos: int
) -> bool:
    """
    Verifica se o IP da requisição excedeu o limite de tentativas na janela.

    Incrementa o contador como efeito colateral — chamar esta função já
    conta como uma tentativa, então cada view chama exatamente uma vez por
    requisição (RF-01, RF-02).

    Args:
        request (HttpRequest): requisição atual; usa ``REMOTE_ADDR`` como
            identificador, não o usuário autenticado (RNF-02, ADR-3).
        chave (str): namespace do limite (ex.: ``"login"``, ``"comentario"``)
            — evita que login e comentário compartilhem o mesmo contador.
        limite (int): número máximo de tentativas permitidas na janela.
        janela_segundos (int): duração da janela, em segundos; o contador
            expira sozinho no cache ao final dela (RF-03).

    Returns:
        bool: True se o limite já foi atingido (a tentativa atual deve ser
        rejeitada); False se a tentativa foi contabilizada normalmente.
    """
    ip = request.META.get("REMOTE_ADDR", "desconhecido")
    cache_key = f"{_PREFIXO_CACHE}:{chave}:{ip}"

    tentativas = cache.get(cache_key, 0)
    if tentativas >= limite:
        return True

    # add() só define o valor se a chave ainda não existir — preserva o TTL
    # original em vez de reiniciar a janela a cada tentativa.
    cache.add(cache_key, 0, timeout=janela_segundos)
    cache.incr(cache_key)
    return False
