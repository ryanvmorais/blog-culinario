"""
Testes do comando ``semear_dados_demo`` e da configuração do Lighthouse CI.

Cobre:
- o comando recusa rodar com ``DEBUG=False`` e é idempotente;
- toda URL da configuração do Lighthouse (``.github/lighthouse/``) responde 200 com os
  dados semeados, e o mobile e o desktop auditam as mesmas páginas com as mesmas
  checagens;
- nenhuma página carrega imagem, script ou CSS de fora: o CI roda sem rede externa.

Estratégia de isolamento: nada é mockado. O ``MEDIA_ROOT`` vai para um diretório
temporário (o comando grava as capas de verdade), e o ``DEBUG=True`` é ligado pela
fixture ``settings`` porque o runner de testes força ``DEBUG=False`` mesmo com o
settings de desenvolvimento.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from django.conf import LazySettings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

from receitas.management.commands.semear_dados_demo import (
    RECEITAS,
    SLUG_RECEITA_AUDITADA,
)
from receitas.models import Comentario, Receita

pytestmark = pytest.mark.django_db

# Pasta da configuração do Lighthouse CI: fica na raiz do repositório, fora do app.
_LIGHTHOUSE = Path(__file__).resolve().parents[1] / ".github" / "lighthouse"

# Recurso de fora: <img src>, <script src> ou <link rel=stylesheet href> absolutos.
# Os <a href> e as meta tags não carregam nada no navegador.
_RECURSO_EXTERNO = re.compile(
    r'<(?:img|script)\b[^>]*\bsrc="https?://'
    r'|<link\b[^>]*\brel="stylesheet"[^>]*\bhref="https?://',
    re.IGNORECASE,
)

# Auditorias que têm asserção própria: a nota geral de acessibilidade (limite de 0,95)
# passaria mesmo com cada uma delas reprovada.
_ASSERCOES_PROPRIAS = (
    "color-contrast",
    "unsized-images",
    "target-size",
    "errors-in-console",
)


@pytest.fixture
def _demo(settings: LazySettings, tmp_path: Path) -> None:
    """
    Liga o ``DEBUG`` e isola a mídia num diretório temporário.

    Args:
        settings (LazySettings): fixture do pytest-django.
        tmp_path (Path): diretório temporário do teste.
    """
    settings.DEBUG = True
    settings.MEDIA_ROOT = tmp_path


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------
def _configuracao(perfil: str) -> dict[str, Any]:
    """
    Lê a configuração do Lighthouse CI de um perfil.

    Args:
        perfil (str): ``"mobile"`` ou ``"desktop"``.

    Returns:
        dict[str, Any]: o bloco ``ci`` do JSON.
    """
    arquivo = _LIGHTHOUSE / f"{perfil}.json"
    bloco: dict[str, Any] = json.loads(arquivo.read_text(encoding="utf-8"))["ci"]
    return bloco


def _caminhos(perfil: str) -> list[str]:
    """
    Lista os caminhos que o Lighthouse CI audita num perfil.

    Args:
        perfil (str): ``"mobile"`` ou ``"desktop"``.

    Returns:
        list[str]: caminhos (``/receitas/``), sem o host do servidor local.
    """
    urls: list[str] = _configuracao(perfil)["collect"]["url"]
    return [re.sub(r"^https?://[^/]+", "", url) for url in urls]


# -----------------------------------------------------------------------------
# O comando
# -----------------------------------------------------------------------------
def test_recusa_rodar_com_debug_desligado() -> None:
    """Dado ``DEBUG=False``, o comando para antes de criar qualquer coisa."""
    with pytest.raises(CommandError, match="DEBUG=True"):
        call_command("semear_dados_demo")
    assert Receita.objects.count() == 0


@pytest.mark.usefixtures("_demo")
def test_cria_as_receitas_com_capa_e_comentarios() -> None:
    """Dado ``DEBUG=True``, cria as receitas publicadas, com capa, e os comentários."""
    call_command("semear_dados_demo")

    assert Receita.objects.filter(publicado=True).count() == len(RECEITAS)
    assert all(receita.imagem_capa for receita in Receita.objects.all())
    assert Comentario.objects.filter(aprovado=True).exists()
    assert Receita.objects.filter(slug=SLUG_RECEITA_AUDITADA).exists()


@pytest.mark.usefixtures("_demo")
def test_rodar_duas_vezes_nao_duplica_nada() -> None:
    """Dado um banco já semeado, rodar de novo não cria receita nem comentário."""
    call_command("semear_dados_demo")
    receitas, comentarios = Receita.objects.count(), Comentario.objects.count()

    call_command("semear_dados_demo")

    assert Receita.objects.count() == receitas
    assert Comentario.objects.count() == comentarios


# -----------------------------------------------------------------------------
# A configuração do Lighthouse
# -----------------------------------------------------------------------------
@pytest.mark.usefixtures("_demo")
@pytest.mark.parametrize("perfil", ["mobile", "desktop"])
def test_toda_url_auditada_responde_200(perfil: str, client: Client) -> None:
    """Dado o banco semeado, cada página auditada existe (senão o CI audita um 404)."""
    call_command("semear_dados_demo")

    respostas = {
        caminho: client.get(caminho).status_code for caminho in _caminhos(perfil)
    }

    assert respostas == dict.fromkeys(_caminhos(perfil), 200)


def test_mobile_e_desktop_auditam_as_mesmas_paginas_com_as_mesmas_checagens() -> None:
    """Dado os dois perfis, só os limites mudam: páginas e auditorias são as mesmas."""
    mobile, desktop = _configuracao("mobile"), _configuracao("desktop")

    assert mobile["collect"]["url"] == desktop["collect"]["url"]
    assert (
        mobile["assert"]["assertions"].keys() == desktop["assert"]["assertions"].keys()
    )
    assert desktop["collect"]["settings"]["preset"] == "desktop"
    assert "preset" not in mobile["collect"]["settings"]


@pytest.mark.parametrize("perfil", ["mobile", "desktop"])
@pytest.mark.parametrize("auditoria", _ASSERCOES_PROPRIAS)
def test_auditorias_com_asserção_própria(perfil: str, auditoria: str) -> None:
    """Dado cada perfil, as auditorias que a nota geral esconde têm asserção de erro."""
    regra = _configuracao(perfil)["assert"]["assertions"][auditoria]

    assert regra[0] == "error"


@pytest.mark.usefixtures("_demo")
def test_nenhuma_pagina_carrega_recurso_de_fora(client: Client) -> None:
    """Dado o banco semeado, nenhuma página puxa imagem, script ou CSS de outro host."""
    call_command("semear_dados_demo")

    for caminho in _caminhos("mobile"):
        html = client.get(caminho).content.decode()
        assert _RECURSO_EXTERNO.search(html) is None, caminho
