"""
Views de autenticação: cadastro, login e logout (spec 004).

Login e logout reaproveitam ``LoginView``/``LogoutView`` do Django (RNF-01)
— só acrescentam a mensagem de feedback (ADR-3). Cadastro precisa de uma
view própria porque o Django não fornece uma pronta. No modo demonstração
(spec 009), o cadastro valida mas não cria a conta.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from blog_culinario.demonstracao import mensagem_cadastro, modo_demonstracao_ligado
from blog_culinario.limitacao import (
    JANELA_LOGIN_SEGUNDOS,
    LIMITE_LOGIN,
    MENSAGEM_LIMITE_LOGIN,
    limite_excedido,
)

from .forms import FormularioCadastro, FormularioEntrar


class CadastroView(FormView):
    """Cria a conta e autentica o usuário automaticamente (ADR-1)."""

    template_name = "usuarios/cadastro.html"
    form_class = FormularioCadastro
    success_url = reverse_lazy("nucleo:home")

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """
        Bloqueia o envio se o visitante excedeu o limite de cadastros.

        A checagem vem antes do formulário (spec 006, adendo, RF-05): acima do
        limite, nada é validado, nem no modo demonstração, e o formulário não
        chega a dizer se um nome de usuário já existe. O contador
        ``"cadastro"`` é separado do login e do comentário.

        Args:
            request (HttpRequest): requisição POST recebida.
            *args (object): argumentos posicionais repassados ao ``super().post()``.
            **kwargs (object): argumentos nomeados repassados ao ``super().post()``.

        Returns:
            HttpResponse: redireciona de volta ao cadastro com mensagem de erro
            se o limite foi atingido; caso contrário, segue o fluxo normal do
            ``FormView``.
        """
        if limite_excedido(request, "cadastro", limite=10, janela_segundos=3600):
            messages.error(
                request, "Muitas tentativas de cadastro. Tente novamente mais tarde."
            )
            return redirect("usuarios:cadastro")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: FormularioCadastro) -> HttpResponse:
        """
        Salva o usuário, autentica a sessão e mostra a mensagem de boas-vindas.

        No modo demonstração (spec 009, RF-03), o formulário já passou por toda
        a validação, mas nada é gravado: a página volta ao cadastro com o aviso
        educativo, no padrão post/redirect/get (ADR-4).

        Args:
            form (FormularioCadastro): formulário já validado.

        Returns:
            HttpResponse: redireciona para ``success_url`` ou, no modo
            demonstração, de volta para o cadastro.
        """
        if modo_demonstracao_ligado():
            messages.info(self.request, mensagem_cadastro())
            return redirect("usuarios:cadastro")
        usuario = form.save()
        login(self.request, usuario)
        messages.success(self.request, f"Bem-vindo(a), {usuario.username}!")
        return super().form_valid(form)


class EntrarView(LoginView):
    """Login nativo do Django, com template, mensagem e limite de tentativas."""

    template_name = "usuarios/login.html"
    # Erros ligados aos campos e sem o autofoco do Django (FormularioAcessivelMixin).
    form_class = FormularioEntrar

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """
        Bloqueia a tentativa se o IP excedeu o limite de tentativas de login.

        Chave por IP, não por username (RNF-02, ADR-3 da spec 006) — evita
        que um atacante contorne o limite variando o usuário testado a cada
        tentativa.

        Args:
            request (HttpRequest): requisição POST recebida.
            *args (object): argumentos posicionais repassados ao ``super().post()``.
            **kwargs (object): argumentos nomeados repassados ao ``super().post()``.

        Returns:
            HttpResponse: redireciona de volta ao login com mensagem de
            erro se o limite foi atingido; caso contrário, segue o fluxo
            normal do ``LoginView``.
        """
        if limite_excedido(
            request,
            "login",
            limite=LIMITE_LOGIN,
            janela_segundos=JANELA_LOGIN_SEGUNDOS,
        ):
            messages.error(request, MENSAGEM_LIMITE_LOGIN)
            return redirect("usuarios:entrar")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        """
        Autentica via ``LoginView`` e acrescenta a mensagem de boas-vindas.

        Args:
            form (AuthenticationForm): formulário já validado pelo ``LoginView``.

        Returns:
            HttpResponse: redireciona para ``?next=`` ou ``LOGIN_REDIRECT_URL``.
        """
        resposta = super().form_valid(form)
        messages.success(
            self.request, f"Bem-vindo(a) de volta, {self.request.user.username}!"
        )
        return resposta


class SairView(LogoutView):
    """Logout nativo do Django — só aceita POST (ADR-2)."""

    # django-stubs tipa next_page como `str | None`; reverse_lazy() devolve um
    # proxy preguiçoso que só vira str quando avaliado — comportamento correto
    # em runtime, só a anotação do stub que é estrita demais aqui.
    next_page = reverse_lazy("nucleo:home")  # type: ignore[assignment]

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """
        Registra a mensagem de despedida antes de encerrar a sessão.

        Args:
            request (HttpRequest): requisição POST recebida.
            *args (object): argumentos posicionais repassados ao ``super().post()``.
            **kwargs (object): argumentos nomeados repassados ao ``super().post()``.

        Returns:
            HttpResponse: redireciona para ``next_page``.
        """
        messages.info(request, "Você saiu da sua conta.")
        return super().post(request, *args, **kwargs)
