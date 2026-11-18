"""
Testes do redesenho de Entrar e Cadastro (spec 012, adendo 2, RF-29 a RF-31).

Conferem o cartão, os rótulos sem dois-pontos, o "(opcional)" do e-mail, a
regra de senha numa frase e o vínculo dessa frase com os validadores do
``AUTH_PASSWORD_VALIDATORS``. O CSS do cartão é conferido em
``nucleo/test_interface.py``; a medida em navegador real fica nas notas do
``design.md`` da spec.

Estratégia de isolamento: ORM e HTTP de teste do Django, sem mock. O cache é
limpo antes de cada teste para o limite de envios do cadastro (spec 006) não
vazar de um teste para o outro.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

from receitas.models import Categoria, Receita
from usuarios.forms import AJUDA_SENHA

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _limpar_cache_de_limitacao() -> None:
    """Zera os contadores de limitação de taxa antes de cada teste (spec 006)."""
    cache.clear()


# -----------------------------------------------------------------------------
# Apoio
# -----------------------------------------------------------------------------
def _rotulos(html: str) -> list[str]:
    """
    Devolve o texto de cada ``<label>`` da página, sem tags e espaços extras.

    Args:
        html (str): HTML da página.

    Returns:
        list[str]: o texto visível de cada rótulo, na ordem da página.
    """
    rotulos = re.findall(r"<label[^>]*>(.*?)</label>", html, flags=re.DOTALL)
    return [" ".join(re.sub(r"<[^>]+>", " ", r).split()) for r in rotulos]


# -----------------------------------------------------------------------------
# Cartão (RF-29)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("rota", "titulo", "troca"),
    [
        ("usuarios:entrar", "Entrar", "Ainda não tem conta?"),
        ("usuarios:cadastro", "Criar conta", "Já tem conta?"),
    ],
)
def test_pagina_de_acesso_fica_num_cartao(
    client: Client, rota: str, titulo: str, troca: str
) -> None:
    """RF-29: título, formulário e troca de página dentro do mesmo cartão."""
    html = client.get(reverse(rota)).content.decode()

    cartao = html[html.index('<div class="cartao-acesso">') :]
    assert f"<h1>{titulo}</h1>" in cartao
    assert '<form class="formulario"' in cartao
    assert f'<p class="cartao-acesso__troca">{troca}' in cartao


# -----------------------------------------------------------------------------
# Rótulos (RF-30)
# -----------------------------------------------------------------------------
def test_entrar_tem_rotulos_sem_dois_pontos(client: Client) -> None:
    """RF-30."""
    html = client.get(reverse("usuarios:entrar")).content.decode()

    assert _rotulos(html) == ["Usuário", "Senha"]


def test_cadastro_tem_rotulos_sem_dois_pontos_e_o_email_opcional(
    client: Client,
) -> None:
    """RF-30, RF-31: só o e-mail pode ficar vazio, e só ele diz isso."""
    html = client.get(reverse("usuarios:cadastro")).content.decode()

    assert _rotulos(html) == [
        "Usuário",
        "E-mail (opcional)",
        "Senha",
        "Confirme a senha",
    ]
    assert html.count('class="formulario__opcional"') == 1


def test_rotulo_do_comentario_tambem_fica_sem_dois_pontos(client: Client) -> None:
    """RF-30: o formulário de comentário segue a regra das páginas de acesso."""
    receita = Receita.objects.create(
        titulo="Bolo de cenoura",
        resumo="Resumo.",
        ingredientes="1 cenoura",
        modo_de_preparo="Misture.",
        tempo_preparo_minutos=10,
        porcoes=1,
        categoria=Categoria.objects.create(nome="Sobremesas"),
        publicado=True,
    )
    client.force_login(User.objects.create_user("leitora", password="senha-longa-1"))

    html = client.get(reverse("receitas:detalhe", args=[receita.slug])).content.decode()

    assert "Comentário" in _rotulos(html)
    assert not [r for r in _rotulos(html) if r.endswith(":")]


# -----------------------------------------------------------------------------
# Regras de senha (RF-31)
# -----------------------------------------------------------------------------
def test_regras_de_senha_aparecem_numa_frase_ligada_ao_campo(client: Client) -> None:
    """RF-31, RNF-14: a frase é a ajuda que o leitor de tela lê com o campo."""
    html = client.get(reverse("usuarios:cadastro")).content.decode()

    campo = re.search(r'<input[^>]*name="password1"[^>]*>', html)
    assert campo is not None
    assert 'aria-describedby="id_password1_helptext"' in campo.group(0)
    assert f'id="id_password1_helptext">{AJUDA_SENHA}</div>' in html
    assert "Sua senha precisa conter" not in html


def test_confirmacao_de_senha_fica_sem_ajuda(client: Client) -> None:
    """RF-31: o rótulo "Confirme a senha" já diz o que a ajuda repetia."""
    html = client.get(reverse("usuarios:cadastro")).content.decode()

    campo = re.search(r'<input[^>]*name="password2"[^>]*>', html)
    assert campo is not None
    assert "aria-describedby" not in campo.group(0)
    assert "id_password2_helptext" not in html
    assert "informada anteriormente" not in html


def test_frase_da_senha_acompanha_os_validadores() -> None:
    """
    RF-31, ADR-15: a frase é fixa, então os validadores não podem mudar sem ela.

    Se este teste falhar, reescreva ``AJUDA_SENHA`` com as regras novas e
    atualize a lista abaixo.
    """
    nomes = [v["NAME"].rsplit(".", 1)[-1] for v in settings.AUTH_PASSWORD_VALIDATORS]
    com_opcoes = [v for v in settings.AUTH_PASSWORD_VALIDATORS if "OPTIONS" in v]

    assert nomes == [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
    # Sem OPTIONS, o MinimumLengthValidator pede 8, o número da frase.
    assert com_opcoes == []
    assert AJUDA_SENHA.startswith("Pelo menos 8 caracteres.")


def test_senha_fora_da_regra_segue_recusada(client: Client) -> None:
    """RF-31: a frase curta não muda a validação; o erro volta sob o campo."""
    resposta = client.post(
        reverse("usuarios:cadastro"),
        {
            "username": "chef-teste",
            "password1": "12345678",
            "password2": "12345678",
        },
    )
    html = resposta.content.decode()

    assert not User.objects.filter(username="chef-teste").exists()
    assert 'class="formulario__erro"' in html


# -----------------------------------------------------------------------------
# Foco e erros para leitor de tela (achados do teste com NVDA)
# -----------------------------------------------------------------------------
def _campo(html: str, nome: str) -> str:
    """
    Devolve a tag ``<input>`` de um campo.

    Args:
        html (str): HTML da página.
        nome (str): atributo ``name`` do campo.

    Returns:
        str: a tag inteira do campo.
    """
    campo = re.search(rf'<input[^>]*name="{nome}"[^>]*>', html)
    assert campo is not None, nome
    return campo.group(0)


@pytest.mark.parametrize("rota", ["usuarios:entrar", "usuarios:cadastro"])
def test_pagina_de_acesso_abre_sem_foco_automatico(client: Client, rota: str) -> None:
    """Com o autofoco, o leitor de tela pulava o título e a conta de demonstração."""
    html = client.get(reverse(rota)).content.decode()

    assert "autofocus" not in html


def test_senha_errada_leva_o_foco_a_mensagem(client: Client) -> None:
    """Sem o foco na mensagem, o leitor de tela não dizia que o login falhou."""
    User.objects.create_user("chef", password="senha-longa-1")

    html = client.post(
        reverse("usuarios:entrar"), {"username": "chef", "password": "errada"}
    ).content.decode()

    erro = re.search(r'<p class="formulario__erro"[^>]*>', html)
    assert erro is not None
    assert 'tabindex="-1"' in erro.group(0)
    assert "autofocus" in erro.group(0)
    assert html.count("autofocus") == 1


def test_envio_vazio_liga_cada_erro_ao_campo_e_foca_o_primeiro(client: Client) -> None:
    """O campo inválido anuncia o motivo, não só "entrada inválida"."""
    html = client.post(reverse("usuarios:entrar"), {}).content.decode()

    usuario = _campo(html, "username")
    senha = _campo(html, "password")
    assert 'aria-describedby="id_username_erro"' in usuario
    assert 'aria-invalid="true"' in usuario
    assert "autofocus" in usuario
    assert 'aria-describedby="id_password_erro"' in senha
    assert "autofocus" not in senha
    assert '<div class="formulario__erros" id="id_username_erro">' in html


def test_erro_na_senha_do_cadastro_mantem_a_ajuda_ligada(client: Client) -> None:
    """Com erro, a senha continua apontando para a frase das regras."""
    html = client.post(reverse("usuarios:cadastro"), {}).content.decode()

    assert 'aria-describedby="id_password1_helptext id_password1_erro"' in _campo(
        html, "password1"
    )
    assert "autofocus" in _campo(html, "username")


@override_settings(MODO_DEMONSTRACAO=True)
def test_mensagem_depois_do_envio_recebe_o_foco(client: Client) -> None:
    """A mensagem chega depois de recarregar; sem foco, o leitor de tela a pulava."""
    resposta = client.post(
        reverse("usuarios:cadastro"),
        {
            "username": "chef-demo",
            "password1": "uma-senha-bem-longa-9",
            "password2": "uma-senha-bem-longa-9",
        },
        follow=True,
    )
    html = resposta.content.decode()

    mensagem = re.search(r'<p class="mensagem mensagem--info"[^>]*>', html)
    assert mensagem is not None
    assert 'tabindex="-1"' in mensagem.group(0)
    assert "autofocus" in mensagem.group(0)


def test_mensagens_so_recebem_o_foco_onde_a_pagina_pede() -> None:
    """O topo das outras páginas segue sem foco; acesso e comentários pedem."""
    raiz = Path(__file__).resolve().parent.parent
    pedem = [
        raiz / "usuarios/templates/usuarios/login.html",
        raiz / "usuarios/templates/usuarios/cadastro.html",
        raiz / "receitas/templates/receitas/detalhe.html",
    ]
    for template in pedem:
        texto = template.read_text(encoding="utf-8")
        assert '{% include "includes/mensagens.html" with focar=True %}' in texto
    base = (raiz / "templates/base.html").read_text(encoding="utf-8")
    assert '{% include "includes/mensagens.html" %}' in base
