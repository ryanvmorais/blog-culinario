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

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client
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
