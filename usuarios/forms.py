"""Formulário de cadastro de usuário (spec 004)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# As quatro regras do AUTH_PASSWORD_VALIDATORS numa frase (spec 012, adendo 2,
# RF-31). O Django gera a ajuda como uma lista de quatro frases longas; esta é a
# mesma regra, curta. Fixa, e não gerada, por isso o
# usuarios/test_paginas_de_acesso.py falha se os validadores mudarem.
AJUDA_SENHA = (
    "Pelo menos 8 caracteres. Evite senhas comuns, só com números ou parecidas "
    "com o seu usuário ou e-mail."
)


class FormularioCadastro(UserCreationForm):
    """
    Cadastro de conta: username + senha (herdados) e email opcional.

    Toda a validação de username único, força de senha
    (``AUTH_PASSWORD_VALIDATORS``) e confirmação de senha já vem da
    classe base — este formulário só acrescenta o campo de email e troca
    os textos de ajuda e de rótulo que o Django traz.
    """

    email = forms.EmailField(
        label="E-mail",
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Monta o formulário com os textos curtos das páginas de acesso.

        O Django descreve o ``username`` com "Obrigatório. 150 caracteres ou
        menos. Letras, números e @/./+/-/_ apenas.", texto que nenhum
        cadastro costuma mostrar; as regras de senha viram uma frase
        (``AJUDA_SENHA``); e a confirmação perde a ajuda "Informe a mesma senha
        informada anteriormente, para verificação.", que o rótulo "Confirme a
        senha" já diz (spec 012, adendo 2, RF-31). A validação continua a
        mesma: o erro de cada regra ainda volta com a mensagem do campo.

        Args:
            *args (Any): argumentos posicionais do ``UserCreationForm``.
            **kwargs (Any): argumentos nomeados do ``UserCreationForm``.
        """
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""
        self.fields["password1"].help_text = AJUDA_SENHA
        self.fields["password2"].label = "Confirme a senha"
        self.fields["password2"].help_text = ""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
