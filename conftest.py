"""
Configuração do pytest compartilhada por todos os apps.

O cache do projeto é em arquivo, na pasta de dados (``blog_culinario/cache.py``,
spec 011). Sem o que está aqui, a suíte criaria a ``django_cache/`` real e
gravaria nela os contadores da limitação de taxa, e um teste herdaria os do
anterior.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from django.test.utils import override_settings
from pytest_django.fixtures import Settings

# Cache da sessão inteira, ligado antes da coleta e desligado no fim.
_cache_da_sessao: override_settings | None = None
_pasta_da_sessao: Path | None = None


def _caches(pasta: Path) -> dict[str, dict[str, object]]:
    """
    Monta o ``CACHES`` do projeto apontando para a pasta pedida.

    Args:
        pasta (Path): pasta do cache.

    Returns:
        dict[str, dict[str, object]]: o ``CACHES`` com o backend do projeto.
    """
    return {
        "default": {
            "BACKEND": "blog_culinario.cache.CacheArquivoAtomico",
            "LOCATION": pasta,
        }
    }


def pytest_configure(config: pytest.Config) -> None:
    """
    Tira o cache da raiz antes da coleta dos testes.

    A coleta já abre o cache: o pytest inspeciona o ``cache`` que os módulos de
    teste importam do Django, e a criação do banco de teste roda o
    ``createcachetable``. Os dois aconteceriam antes de qualquer fixture.

    Args:
        config (pytest.Config): configuração do pytest (não usada).
    """
    global _cache_da_sessao, _pasta_da_sessao
    _pasta_da_sessao = Path(tempfile.mkdtemp(prefix="blog-culinario-cache-"))
    _cache_da_sessao = override_settings(CACHES=_caches(_pasta_da_sessao))
    _cache_da_sessao.enable()


def pytest_unconfigure(config: pytest.Config) -> None:
    """
    Desliga o cache da sessão e apaga a pasta dele.

    Args:
        config (pytest.Config): configuração do pytest (não usada).
    """
    if _cache_da_sessao is not None:
        _cache_da_sessao.disable()
    if _pasta_da_sessao is not None:
        shutil.rmtree(_pasta_da_sessao, ignore_errors=True)


@pytest.fixture(autouse=True)
def _cache_em_pasta_temporaria(settings: Settings, tmp_path: Path) -> None:
    """
    Põe o cache de cada teste numa pasta temporária própria, vazia.

    Trocar o ``CACHES`` dispara o sinal ``setting_changed``, e o Django recria
    as conexões de cache com a pasta nova.

    Args:
        settings (Settings): fixture do pytest-django que troca uma
            configuração só durante o teste.
        tmp_path (Path): pasta temporária do teste, criada pelo pytest.
    """
    settings.CACHES = _caches(tmp_path / "django_cache")
