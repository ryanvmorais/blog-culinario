"""Formulários de cadastro e de login (spec 004; acessibilidade da spec 012)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

# As quatro regras do AUTH_PASSWORD_VALIDATORS numa frase (spec 012, adendo 2,
# RF-31). O Django gera a ajuda como uma lista de quatro frases longas; esta é a
# mesma regra, curta. Fixa, e não gerada, por isso o
# usuarios/test_paginas_de_acesso.py falha se os validadores mudarem.
AJUDA_SENHA = (
    "Pelo menos 8 caracteres. Evite senhas comuns, só com números ou parecidas "
    "com o seu usuário ou e-mail."
)


# -----------------------------------------------------------------------------
# Acessibilidade dos formulários de acesso
# -----------------------------------------------------------------------------
class FormularioAcessivelMixin(forms.BaseForm):
    """
    Liga cada erro ao seu campo e decide onde o foco começa.

    O Django marca o campo inválido com ``aria-invalid``, mas a mensagem fica
    num parágrafo solto: o leitor de tela dizia "entrada inválida" sem o
    motivo. Aqui o ``aria-describedby`` do campo passa a apontar também para o
    bloco de erros (``<id>_erro``, escrito pelo ``usuarios/campo.html``).

    O foco automático que o Django põe no nome de usuário sai: com ele, o
    leitor de tela começava no campo e pulava o título e a conta de
    demonstração. Com erro de campo, o foco vai para o primeiro campo
    inválido; com erro do formulário inteiro (senha errada), ele fica com o
    template, que foca a mensagem.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Monta o formulário sem o foco automático do Django.

        Args:
            *args (Any): argumentos posicionais do formulário de base.
            **kwargs (Any): argumentos nomeados do formulário de base.
        """
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.pop("autofocus", None)

    def full_clean(self) -> None:
        """
        Valida e, havendo erro, liga as mensagens aos campos e escolhe o foco.

        Roda depois da validação do Django, quando os erros já existem e os
        campos ainda não foram desenhados.
        """
        super().full_clean()
        if not self.is_bound or not self.auto_id:
            return
        invalidos = [nome for nome in self.fields if nome in self.errors]
        for nome in invalidos:
            campo = self[nome]
            descricoes = [f"{campo.auto_id}_erro"]
            if campo.help_text:
                descricoes.insert(0, f"{campo.auto_id}_helptext")
            campo.field.widget.attrs["aria-describedby"] = " ".join(descricoes)
        if invalidos and not self.non_field_errors():
            self.fields[invalidos[0]].widget.attrs["autofocus"] = True


# -----------------------------------------------------------------------------
# Formulários
# -----------------------------------------------------------------------------
class FormularioEntrar(FormularioAcessivelMixin, AuthenticationForm):
    """Login nativo do Django, com os erros ligados aos campos e sem autofoco."""


class FormularioCadastro(FormularioAcessivelMixin, UserCreationForm):
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
