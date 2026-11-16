"""
Backend de cache em arquivo com ``add()`` e ``incr()`` atômicos (spec 011).

A limitação de taxa (``blog_culinario/limitacao.py``, spec 006) conta as
tentativas de cada IP com ``cache.add()`` e ``cache.incr()``. Com o gunicorn em
mais de um worker, o contador precisa ficar fora dos processos, e o
``FileBasedCache`` do Django guarda tudo em arquivos de uma pasta que todos os
workers veem. Mas ele tem dois defeitos para contar:

- o ``add()`` faz ``has_key()`` e depois ``set()``, sem trava: pedidos
  simultâneos veem a chave ausente e todos gravam;
- o ``incr()`` herdado do ``BaseCache`` faz ``get()`` + ``set()`` sem trava e
  grava com o ``TIMEOUT`` padrão do ``CACHES``, o que reiniciaria a janela da
  limitação a cada tentativa.

Este backend passa os dois por uma trava exclusiva de arquivo, que vale entre
threads e entre processos, e faz o ``incr()`` manter a validade que a chave já
tinha, como o ``LocMemCache`` e o Redis fazem (spec 011, ADR-4).
"""

from __future__ import annotations

import os
import pickle
import time
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.filebased import FileBasedCache
from django.core.files import locks

# Fora do padrão *.djcache do FileBasedCache: o _cull() e o clear() não apagam
# a trava, e ela não conta como entrada do cache.
NOME_ARQUIVO_TRAVA = "reserva.lock"


class CacheArquivoAtomico(FileBasedCache):
    """
    ``FileBasedCache`` cujo ``add()`` e ``incr()`` são atômicos entre processos.

    ``get()``, ``set()`` e ``delete()`` seguem como no Django. Uma trava única
    para a pasta basta: cada contagem dura milissegundos, e o tráfego de uma
    demonstração não chega a enfileirar pedidos nela.

    Attributes:
        caminho_trava (str): arquivo da pasta do cache usado como trava
            exclusiva do ``add()`` e do ``incr()``.
    """

    def __init__(self, dir: str, params: dict[str, Any]) -> None:
        """
        Inicializa o cache e guarda o caminho do arquivo de trava.

        Args:
            dir (str): pasta do cache (o ``LOCATION`` do ``CACHES``).
            params (dict[str, Any]): demais opções do ``CACHES``.
        """
        super().__init__(dir, params)
        self._pasta = os.path.abspath(dir)
        self.caminho_trava = os.path.join(self._pasta, NOME_ARQUIVO_TRAVA)

    @contextmanager
    def _trava(self) -> Iterator[None]:
        """
        Segura a trava exclusiva da pasta enquanto o bloco roda.

        Cada chamada abre o arquivo de novo: a trava é do arquivo aberto, então
        duas threads do mesmo processo também se esperam.

        Yields:
            None: o bloco roda com a trava segura.
        """
        # A pasta pode ter sido apagada desde a inicialização (o FileBasedCache
        # também recria antes de gravar).
        os.makedirs(self._pasta, exist_ok=True)
        with open(self.caminho_trava, "ab") as trava:
            locks.lock(trava, locks.LOCK_EX)
            try:
                yield
            finally:
                locks.unlock(trava)

    def add(
        self,
        key: Any,
        value: Any,
        timeout: float | None = DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> bool:
        """
        Grava a chave só se ela ainda não existir, sem corrida entre pedidos.

        Args:
            key (Any): chave do cache.
            value (Any): valor a gravar.
            timeout (float | None): validade em segundos; ``None`` não expira.
                Padrão: o ``TIMEOUT`` do ``CACHES``.
            version (int | None): versão da chave. Padrão: a do ``CACHES``.

        Returns:
            bool: ``True`` se gravou (a chave não existia ou tinha expirado),
            ``False`` se ela já existia.
        """
        with self._trava():
            return super().add(key, value, timeout, version)

    def incr(self, key: Any, delta: int = 1, version: int | None = None) -> int:
        """
        Soma ``delta`` ao valor da chave, mantendo a validade que ela tinha.

        Lê o arquivo da chave no formato do ``FileBasedCache`` (a validade em
        segundos desde a época, gravada primeiro, e o valor comprimido depois) e
        regrava o valor somado com o tempo que faltava para a validade.

        Args:
            key (Any): chave do cache.
            delta (int): quanto somar. Padrão: 1.
            version (int | None): versão da chave. Padrão: a do ``CACHES``.

        Returns:
            int: o valor depois da soma.

        Raises:
            ValueError: se a chave não existe ou já expirou (o contrato do
                ``incr()`` do Django).
        """
        with self._trava():
            # _key_to_file é interno do FileBasedCache e não está nos stubs; o
            # teste da validade preservada acusa se uma versão nova o mudar.
            arquivo = self._key_to_file(key, version)  # type: ignore[attr-defined]
            try:
                with open(arquivo, "rb") as conteudo:
                    validade = pickle.load(conteudo)
                    valor = pickle.loads(zlib.decompress(conteudo.read()))
            except (FileNotFoundError, EOFError):
                raise ValueError(f"Key '{key}' not found") from None

            restante = None if validade is None else validade - time.time()
            if restante is not None and restante <= 0:
                self.delete(key, version)
                raise ValueError(f"Key '{key}' not found")

            novo_valor: int = valor + delta
            self.set(key, novo_valor, timeout=restante, version=version)
            return novo_valor
