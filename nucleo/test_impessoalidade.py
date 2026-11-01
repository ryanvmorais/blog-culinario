"""
Testes de que o repositório fala com quem o clonou, não com o mantenedor.

Tudo o que é versionado é lido por quem clona o projeto: o nome do mantenedor
fica restrito à autoria (``LICENSE``), e o ``CLAUDE.md`` descreve o projeto sem
apontar para skills ou pastas pessoais que só existem na máquina de quem o
escreveu. Os testes varrem o texto dos arquivos versionados e falham quando uma
dessas referências volta.

Estratégia de isolamento: só a lista de arquivos do Git (``git ls-files``) e o
texto deles são lidos, sem banco nem cliente HTTP. Sem o Git disponível (um
tarball do código, por exemplo), os testes são pulados.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent

# Nome do mantenedor como palavra inteira: as URLs e o e-mail de contato ficam em
# minúsculas e colados ("ryanvmorais"), então só a prosa e a assinatura casam.
NOME = re.compile(r"\bRyan\b")

# Autoria é exceção: a licença leva o nome, e este arquivo precisa citá-lo para
# testar a regra.
COM_NOME_PERMITIDO = {"LICENSE", "nucleo/test_impessoalidade.py"}

# Skill pessoal ("/idioma", "/spec"...) ou a pasta de configuração do Claude da
# máquina do mantenedor. O lookbehind evita casar caminhos como "docs/stack.md".
PESSOAL = re.compile(
    r"(?<![\w./-])/(?:idioma|spec|estilo-arquivos|fechar-sessao|atualizar-[a-z]+"
    r"|revisar-dependabot|nova-interface|stack|novo-projeto|qualidade-python"
    r"|auditoria-[a-z]+|limpar-branches|preparar-release)\b|~/\.claude"
)


# -----------------------------------------------------------------------------
# Apoio
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def versionados() -> dict[str, str]:
    """
    Lê o texto de cada arquivo versionado, indexado pelo caminho relativo.

    Returns:
        dict[str, str]: Caminho com ``/`` como separador e o conteúdo em UTF-8.
            Arquivo binário (fontes, imagens) fica de fora.
    """
    try:
        saida = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=RAIZ,
            check=True,
            capture_output=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("sem o Git, não há lista de arquivos versionados")

    textos: dict[str, str] = {}
    for bruto in saida.decode("utf-8").split("\0"):
        if not bruto:
            continue
        try:
            textos[bruto] = (RAIZ / bruto).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return textos


# -----------------------------------------------------------------------------
# Testes
# -----------------------------------------------------------------------------


def test_a_varredura_enxerga_os_arquivos_do_projeto(
    versionados: dict[str, str],
) -> None:
    """Guarda contra uma lista vazia, que deixaria os outros testes passarem à toa."""
    assert "README.md" in versionados
    assert "CLAUDE.md" in versionados


def test_o_nome_do_mantenedor_so_aparece_na_autoria(
    versionados: dict[str, str],
) -> None:
    """O nome do mantenedor só aparece na autoria (``LICENSE``)."""
    com_nome = sorted(
        caminho
        for caminho, texto in versionados.items()
        if caminho not in COM_NOME_PERMITIDO and NOME.search(texto)
    )
    assert com_nome == []


def test_o_claude_md_nao_aponta_para_skills_pessoais(
    versionados: dict[str, str],
) -> None:
    """O ``CLAUDE.md`` descreve o projeto sem apontar para skills pessoais."""
    pessoais = sorted(
        caminho
        for caminho, texto in versionados.items()
        if (caminho == "CLAUDE.md" or caminho.startswith(".claude/"))
        and PESSOAL.search(texto)
    )
    assert pessoais == []
