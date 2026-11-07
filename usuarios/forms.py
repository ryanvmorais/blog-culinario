"""Formulário de cadastro de usuário (spec 004)."""

from __future__ import annotations

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

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
