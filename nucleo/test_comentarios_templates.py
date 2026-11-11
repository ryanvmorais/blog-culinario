"""
Testes de que os comentários dos templates não chegam ao HTML entregue.

Nota interna e marcador de seção são comentários do Django: ``{# #}`` numa linha
e ``{% comment %}…{% endcomment %}`` em várias. O ``<!-- -->`` iria para o
navegador de cada visitante, e o Django executa as tags escritas dentro dele. Um
``{# #}`` quebrado em linhas o Django mostra como texto na página.

Estratégia de isolamento: só o texto dos templates é lido, sem banco nem cliente
HTTP. O ``docs/design-system.html`` não entra: é HTML aberto por ``file://``,
sem motor de template, e lá ``<!-- -->`` é a única forma de comentário.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent

# Pastas de templates do projeto e dos apps (as do .venv ficam de fora).
TEMPLATES = sorted(
    caminho
    for pasta in [RAIZ / "templates", *RAIZ.glob("*/templates")]
    for caminho in pasta.rglob("*.html")
)

# "{#" seguido de uma quebra de linha antes do "#}": comentário quebrado.
COMENTARIO_QUEBRADO = re.compile(r"\{#(?:(?!#\})[^\n])*\n")


# -----------------------------------------------------------------------------
# Testes
# -----------------------------------------------------------------------------


def test_ha_templates_para_conferir() -> None:
    """Sem templates achados, os testes abaixo passariam sem conferir nada."""
    assert TEMPLATES


@pytest.mark.parametrize(
    "caminho", TEMPLATES, ids=lambda c: c.relative_to(RAIZ).as_posix()
)
def test_template_nao_usa_comentario_html(caminho: Path) -> None:
    """Comentário para quem mantém o código fica fora do HTML entregue."""
    assert "<!--" not in caminho.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "caminho", TEMPLATES, ids=lambda c: c.relative_to(RAIZ).as_posix()
)
def test_comentario_de_uma_linha_nao_quebra(caminho: Path) -> None:
    """Bloco de várias linhas vai em ``{% comment %}``, nunca em ``{# #}``."""
    assert not COMENTARIO_QUEBRADO.search(caminho.read_text(encoding="utf-8"))
