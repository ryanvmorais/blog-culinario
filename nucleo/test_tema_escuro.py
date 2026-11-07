"""
Testes do tema escuro do sistema e do contraste das duas paletas (spec 008, RF-15).

Lê ``static/css/tokens.css`` e calcula o contraste WCAG de cada par de cores em
uso, no tema claro (o ``:root``) e no escuro (o bloco ``prefers-color-scheme``).
Nenhum navegador é aberto: o que se prova é que as variáveis, uma vez aplicadas,
passam de 4,5:1 (texto) e 3:1 (borda de campo).

Estratégia de isolamento: só leitura de arquivo, sem banco nem mock.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nucleo.test_interface import _contraste

CSS_TOKENS = (
    Path(__file__).resolve().parent.parent / "static/css/tokens.css"
).read_text(encoding="utf-8")

# Pares (texto, fundo) que o site realmente desenha, com o mínimo de contraste.
TEXTO_SOBRE_FUNDO = [
    ("--cor-texto", "--cor-fundo", 4.5),
    ("--cor-texto", "--cor-superficie", 4.5),
    ("--cor-texto-suave", "--cor-fundo", 4.5),
    ("--cor-texto-suave", "--cor-superficie", 4.5),
    ("--cor-primaria", "--cor-fundo", 4.5),
    ("--cor-primaria", "--cor-superficie", 4.5),
    ("--cor-texto-invertido", "--cor-primaria", 4.5),  # texto do botão primário
    ("--cor-primaria-escura", "--cor-primaria-clara", 4.5),  # selo e mensagem de ok
    ("--cor-destaque-escura", "--cor-superficie", 4.5),  # categoria do cartão
    ("--cor-erro", "--cor-erro-fundo", 4.5),
    ("--cor-texto", "--cor-borda", 4.5),  # mensagem de informação
    ("--cor-borda-campo", "--cor-superficie", 3.0),  # WCAG 1.4.11
    ("--cor-borda-campo", "--cor-fundo", 3.0),
]


def _bloco_escuro() -> str:
    """
    Devolve o corpo do ``:root`` dentro de ``@media (prefers-color-scheme: dark)``.

    Returns:
        str: texto das variáveis do tema escuro.

    Raises:
        AssertionError: se o bloco não existe em ``tokens.css``.
    """
    achado = re.search(
        r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}\s*\}",
        CSS_TOKENS,
        flags=re.DOTALL,
    )
    assert achado, "bloco prefers-color-scheme: dark ausente"
    return achado.group(1)


def _paleta(corpo: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """
    Lê as variáveis de cor ``#rrggbb`` de um bloco de CSS.

    Args:
        corpo (str): texto com declarações ``--nome: #rrggbb;``.
        base (dict[str, str] | None, optional): paleta de partida, que o bloco
            sobrescreve (o tema escuro herda o que não redefine). Padrão: ``None``.

    Returns:
        dict[str, str]: nome da variável para a cor hexadecimal.
    """
    paleta = dict(base or {})
    paleta.update(re.findall(r"(--cor-[\w-]+):\s*(#[0-9a-fA-F]{6})\b", corpo))
    return paleta


CLARO = _paleta(CSS_TOKENS[: CSS_TOKENS.index("@media (prefers-color-scheme: dark)")])
ESCURO = _paleta(_bloco_escuro(), base=CLARO)


@pytest.mark.parametrize(("texto", "fundo", "minimo"), TEXTO_SOBRE_FUNDO)
@pytest.mark.parametrize("paleta", [CLARO, ESCURO], ids=["tema-claro", "tema-escuro"])
def test_par_de_cores_passa_no_contraste_minimo(
    paleta: dict[str, str], texto: str, fundo: str, minimo: float
) -> None:
    """RF-08 e RF-15: cada par em uso passa de 4,5:1 (texto) ou 3:1 (borda)."""
    assert _contraste(paleta[texto], paleta[fundo]) >= minimo, (texto, fundo)


def test_tema_escuro_redefine_so_cores_e_sombras() -> None:
    """RF-15, ADR-3: nenhuma propriedade de componente entra no bloco escuro."""
    nomes = re.findall(r"(--[\w-]+):", _bloco_escuro())

    assert nomes, "o bloco escuro está vazio"
    assert all(n.startswith(("--cor-", "--sombra-")) for n in nomes)


def test_tema_escuro_muda_o_fundo_e_o_texto() -> None:
    """RF-15: o tema escuro de fato inverte fundo e texto."""
    assert ESCURO["--cor-fundo"] != CLARO["--cor-fundo"]
    assert ESCURO["--cor-texto"] != CLARO["--cor-texto"]
    assert _contraste(ESCURO["--cor-fundo"], "#000000") < _contraste(
        CLARO["--cor-fundo"], "#000000"
    )


def test_root_declara_os_dois_esquemas_para_controles_nativos() -> None:
    """RF-15: sem ``color-scheme: light dark`` a rolagem fica clara no escuro."""
    assert "color-scheme: light dark;" in CSS_TOKENS
