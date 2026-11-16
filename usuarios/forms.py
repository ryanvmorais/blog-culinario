"""Formulário de cadastro de usuário (spec 004)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class FormularioCadastro(UserCreationForm):
    """
    Cadastro de conta: username + senha (herdados) e email opcional.

    Toda a validação de username único, força de senha
    (``AUTH_PASSWORD_VALIDATORS``) e confirmação de senha já vem da
    classe base — este formulário só acrescenta o campo de email.
    """

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Monta o formulário sem a ajuda padrão do campo de usuário.

        O Django descreve o ``username`` com "Obrigatório. 150 caracteres ou
        menos. Letras, números e @/./+/-/_ apenas.", texto que nenhum
        cadastro costuma mostrar. A validação continua a mesma: um nome
        inválido ou longo demais ainda volta com a mensagem de erro do campo.

        Args:
            *args (Any): argumentos posicionais do ``UserCreationForm``.
            **kwargs (Any): argumentos nomeados do ``UserCreationForm``.
        """
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
