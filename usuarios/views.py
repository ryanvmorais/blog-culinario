"""
Views de autenticação: cadastro, login e logout (spec 004).

Login e logout reaproveitam ``LoginView``/``LogoutView`` do Django (RNF-01)
— só acrescentam a mensagem de feedback (ADR-3). Cadastro precisa de uma
view própria porque o Django não fornece uma pronta. No modo demonstração
(spec 009), o cadastro valida mas não cria a conta. O login do Admin passa
pela ``entrar_no_admin``, que aplica o mesmo limite de tentativas do login do
site, no mesmo contador.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from blog_culinario.demonstracao import mensagem_cadastro, modo_demonstracao_ligado
from blog_culinario.limitacao import limite_excedido

from .forms import FormularioCadastro

# Limite de tentativas de login por IP (spec 006, RF-01), igual no login do
# site e no do Admin. A chave é a mesma nos dois: alternar entre eles não
# dobra as tentativas da janela.
CHAVE_LIMITE_LOGIN = "login"
LIMITE_LOGIN = 5
JANELA_LOGIN_SEGUNDOS = 300
MENSAGEM_LIMITE_LOGIN = "Muitas tentativas de login. Tente novamente em alguns minutos."


class CadastroView(FormView):
    """Cria a conta e autentica o usuário automaticamente (ADR-1)."""

    template_name = "usuarios/cadastro.html"
    form_class = FormularioCadastro
    success_url = reverse_lazy("nucleo:home")

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
            request, CHAVE_LIMITE_LOGIN, LIMITE_LOGIN, JANELA_LOGIN_SEGUNDOS
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


def entrar_no_admin(request: HttpRequest) -> HttpResponse:
    """
    Login do Admin com o mesmo limite de tentativas do login do site.

    O ``/admin/login/`` é uma view do ``django.contrib.admin``, que o limite da
    spec 006 não cobria. Esta função vem antes dela nas rotas: no envio do
    formulário, conta a tentativa no contador do login do site e, passado o
    limite, volta à tela de login com a mensagem, sem conferir a senha (conferir
    diria a quem tenta se ela estava certa). Fora isso, o Admin responde como
    sempre.

    Args:
        request (HttpRequest): requisição recebida em ``/admin/login/``.

    Returns:
        HttpResponse: a tela de login do Admin de novo (com o ``?next=`` do
        pedido) se o limite foi atingido; senão, a resposta do próprio Admin.
    """
    if request.method == "POST" and limite_excedido(
        request, CHAVE_LIMITE_LOGIN, LIMITE_LOGIN, JANELA_LOGIN_SEGUNDOS
    ):
        messages.error(request, MENSAGEM_LIMITE_LOGIN)
        return redirect(request.get_full_path())
    return admin.site.login(request)
