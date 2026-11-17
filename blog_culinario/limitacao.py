"""
Limitação de taxa simples baseada no cache do Django (spec 006).

Sem dependência nova (RNF-01): usa o cache do Django para contar tentativas
por IP numa janela de tempo. O cache é em arquivo, compartilhado entre os
workers do gunicorn, com ``add()`` e ``incr()`` atômicos
(``blog_culinario/cache.py``, spec 011). Compartilhado entre ``usuarios``
(login e cadastro), ``receitas`` (comentário) e o site do Admin
(``blog_culinario/site_admin.py``) — por isso vive aqui, no pacote do
projeto, e não dentro de um app de domínio (ADR-1 da spec 006).

O contador é por rede, não por endereço (adendo da spec 006, RF-06): no IPv6,
todos os endereços de um mesmo /64 dividem um contador só.
"""

from __future__ import annotations

import ipaddress

from django.core.cache import cache
from django.http import HttpRequest

from blog_culinario.origem import ip_do_visitante

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_PREFIXO_CACHE = "limite"

# O login público e o do Admin dividem estes valores e o mesmo contador
# (adendo da spec 006, decisão resolvida 2): contadores separados dariam o
# dobro de tentativas a quem alternasse entre as duas telas.
LIMITE_LOGIN = 5
JANELA_LOGIN_SEGUNDOS = 300
MENSAGEM_LIMITE_LOGIN = "Muitas tentativas de login. Tente novamente em alguns minutos."

# Uma operadora entrega a cada cliente IPv6 pelo menos um /64 inteiro; contar
# por endereço daria um contador zerado a cada endereço do bloco (ADR-7).
_PREFIXO_IPV6 = 64


# ---------------------------------------------------------------------------
# Identificação do visitante
# ---------------------------------------------------------------------------


def _identificador_de_rede(ip: str) -> str:
    """
    Devolve a parte do endereço que identifica o visitante no contador.

    Args:
        ip (str): o que o ``ip_do_visitante()`` devolveu: um IPv4, um IPv6 ou,
            sem ``REMOTE_ADDR``, o texto ``"desconhecido"``.

    Returns:
        str: o IPv4 normalizado; o IPv4 contido num IPv6 da forma
        ``::ffff:a.b.c.d``; a rede /64 de outro IPv6 (``2001:db8:1:2::/64``);
        ou o próprio texto, se ele não é um endereço IP.
    """
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(endereco, ipaddress.IPv4Address):
        return str(endereco)
    if endereco.ipv4_mapped is not None:
        return str(endereco.ipv4_mapped)
    return str(ipaddress.IPv6Network((endereco, _PREFIXO_IPV6), strict=False))


# ---------------------------------------------------------------------------
# Limite
# ---------------------------------------------------------------------------


def limite_excedido(
    request: HttpRequest, chave: str, limite: int, janela_segundos: int
) -> bool:
    """
    Verifica se o visitante excedeu o limite de tentativas na janela.

    Incrementa o contador como efeito colateral — chamar esta função já
    conta como uma tentativa, então cada view chama exatamente uma vez por
    requisição (RF-01, RF-02). A tentativa recusada também soma, sem efeito
    visível: o contador não estende a janela, e a recusa dura até ela acabar.

    Args:
        request (HttpRequest): requisição atual; o identificador é a rede do
            IP do visitante (``ip_do_visitante``: o ``CF-Connecting-IP`` com a
            trava de origem ligada, senão o ``REMOTE_ADDR``, spec 011), não o
            usuário autenticado (RNF-02, ADR-3, RF-06).
        chave (str): namespace do limite (ex.: ``"login"``, ``"cadastro"``,
            ``"comentario"``) — evita que formulários diferentes compartilhem
            o mesmo contador.
        limite (int): número máximo de tentativas permitidas na janela.
        janela_segundos (int): duração da janela, em segundos; o contador
            expira sozinho no cache ao final dela (RF-03).

    Returns:
        bool: True se o limite já foi atingido (a tentativa atual deve ser
        rejeitada); False se a tentativa foi contabilizada normalmente.
    """
    rede = _identificador_de_rede(ip_do_visitante(request))
    cache_key = f"{_PREFIXO_CACHE}:{chave}:{rede}"

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
