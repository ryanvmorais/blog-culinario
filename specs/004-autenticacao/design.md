---
feature: Autenticação de usuários (cadastro, login, logout)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 004 — Autenticação de usuários — design

## Visão geral da abordagem

`django.contrib.auth` cobre login/logout prontos; só o cadastro precisa de
uma view própria (o Django não fornece uma). Três views em `usuarios/views.py`,
um form em `usuarios/forms.py`, três templates, e duas mudanças
transversais: `base.html` ganha uma área de mensagens
(`django.contrib.messages`) e a navbar passa a refletir
`request.user.is_authenticated`.

## Layout de módulos

```
usuarios/
  forms.py     # FormularioCadastro (UserCreationForm + email opcional)
  views.py     # CadastroView, EntrarView (LoginView), SairView (LogoutView)
  urls.py      # cadastro/, entrar/, sair/
  templates/usuarios/
    cadastro.html
    login.html
templates/
  base.html              # + área de mensagens
  includes/navbar.html   # + estado de autenticação
  includes/mensagens.html  # novo include, renderiza django.contrib.messages
static/css/base.css      # + .formulario (forms de auth) e .mensagens
blog_culinario/
  settings/base.py  # + LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL
  urls.py            # + path("usuarios/", include("usuarios.urls"))
```

## Componentes

### `FormularioCadastro` (`usuarios/forms.py`, RF-01)

Subclasse de `UserCreationForm` acrescentando `email` como
`forms.EmailField(required=False)`. Toda a validação de username único,
senha (via `AUTH_PASSWORD_VALIDATORS`) e confirmação de senha já vem
pronta da classe base — zero lógica de validação escrita à mão.

### `CadastroView` (`FormView`, RF-01, RF-06, ADR-1)

```python
class CadastroView(FormView):
    template_name = "usuarios/cadastro.html"
    form_class = FormularioCadastro
    success_url = reverse_lazy("nucleo:home")

    def form_valid(self, form):
        usuario = form.save()
        login(self.request, usuario)
        messages.success(self.request, f"Bem-vindo(a), {usuario.username}!")
        return super().form_valid(form)
```

### `EntrarView` (`LoginView`, RF-02, RF-05, RF-06, RNF-01)

Subclasse só para acrescentar a mensagem de boas-vindas; todo o resto
(autenticação, tratamento de `?next=`, erro genérico de credencial) é
comportamento padrão do `LoginView`.

```python
class EntrarView(LoginView):
    template_name = "usuarios/login.html"

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f"Bem-vindo(a) de volta, {self.request.user.username}!")
        return resposta
```

### `SairView` (`LogoutView`, RF-03, RF-06, ADR-2)

```python
class SairView(LogoutView):
    next_page = reverse_lazy("nucleo:home")

    def post(self, request, *args, **kwargs):
        messages.info(request, "Você saiu da sua conta.")
        return super().post(request, *args, **kwargs)
```

### Mensagens (`templates/includes/mensagens.html`, RF-06, ADR-3)

Novo include, chamado de `base.html` logo após a navbar, iterando
`{% for message in messages %}` — usa as tags padrão do
`django.contrib.messages` (`success`, `info`, `error`, ...) como classe
CSS (`mensagem--{{ message.tags }}`).

### Navbar com estado de autenticação (`templates/includes/navbar.html`, RF-04)

```html
{% if user.is_authenticated %}
  <span>Olá, {{ user.username }}</span>
  <form method="post" action="{% url 'usuarios:sair' %}">
    {% csrf_token %}
    <button type="submit" class="link-botao">Sair</button>
  </form>
{% else %}
  <a href="{% url 'usuarios:entrar' %}">Entrar</a>
  <a href="{% url 'usuarios:cadastro' %}">Cadastrar</a>
{% endif %}
```

## Modelo de dados

Nenhum model novo — usa o `User` padrão do `django.contrib.auth`
(`settings.AUTH_USER_MODEL`, já referenciado por `Receita.autor` desde a
spec 001).

## Interfaces

| Método | URL | View | Nome |
|---|---|---|---|
| GET/POST | `/usuarios/cadastro/` | `CadastroView` | `usuarios:cadastro` |
| GET/POST | `/usuarios/entrar/` | `EntrarView` | `usuarios:entrar` |
| POST | `/usuarios/sair/` | `SairView` | `usuarios:sair` |

`settings/base.py` ganha:
```python
LOGIN_URL = "usuarios:entrar"
LOGIN_REDIRECT_URL = "nucleo:home"
LOGOUT_REDIRECT_URL = "nucleo:home"
```

## ADRs

### ADR-1 — Cadastro autentica automaticamente após criar a conta

**Decisão.** `CadastroView.form_valid()` chama `login(request, usuario)`
logo após `form.save()`.
**Alternativas.** Redirecionar para a página de login após o cadastro,
exigindo que o usuário entre manualmente em seguida.
**Porquê.** Sem verificação de email (não-objetivo), não há motivo para
exigir uma segunda etapa manual — a conta já está pronta para uso no
momento em que é criada.
**Trade-off.** Nenhum relevante dado o escopo (sem confirmação de email).

### ADR-2 — Logout via formulário POST, não link GET

**Decisão.** "Sair" na navbar é um `<button>` dentro de um
`<form method="post">`, não um `<a href>`.
**Alternativas.** Link simples `<a href="{% url 'usuarios:sair' %}">`.
**Porquê.** Desde o Django 4.1, `LogoutView` só aceita `POST` — um `GET`
de logout é uma vulnerabilidade conhecida (um link/imagem em página de
terceiro poderia deslogar a vítima sem ação consciente). Não é uma escolha
de estilo, é a única forma que o Django permite.
**Trade-off.** O botão de "Sair" precisa de um pouco de CSS
(`.link-botao`) para não parecer um `<button>` de formulário cru — mais
markup que um link simples, mas correto por padrão do framework.

### ADR-3 — `django.contrib.messages` em vez de mensagens ad-hoc

**Decisão.** Feedback de cadastro/login/logout usa
`django.contrib.messages` (já instalado desde a fundação do projeto, mas
nunca renderizado em nenhum template).
**Alternativas.** Passar uma variável de contexto customizada
(`mensagem_sucesso`) em cada view.
**Porquê.** É o mecanismo nativo do Django para "mensagem que sobrevive a
um redirect" (guardada na sessão/cookie) — exatamente o que login/logout/
cadastro precisam, já que todos redirecionam. Reinventar isso seria
duplicar o framework.
**Trade-off.** Nenhum relevante.

## Impacto no código existente

- `blog_culinario/settings/base.py`: + `LOGIN_URL`, `LOGIN_REDIRECT_URL`,
  `LOGOUT_REDIRECT_URL`.
- `blog_culinario/urls.py`: + `include("usuarios.urls")`.
- `templates/base.html`: + `{% include "includes/mensagens.html" %}` logo
  após a navbar.
- `templates/includes/navbar.html`: bloco condicional por
  `user.is_authenticated` (RF-04).
- `static/css/base.css`: nova seção com `.formulario` (label+input
  empilhados, para cadastro/login), `.link-botao` (botão de logout com
  cara de link) e `.mensagens`/`.mensagem--*` (cores por `message.tags`).

## Estratégia de testes

`pytest` + `pytest-django`, builders locais em `usuarios/tests.py`
(`_dados_cadastro(**kwargs)` para o payload do formulário). RF-05 é
testado batendo direto em `/usuarios/entrar/?next=/receitas/` com
credenciais válidas e conferindo o redirect — a spec de comentários
(próxima) reusa a mesma infraestrutura (`LOGIN_URL`) numa rota
`@login_required` de verdade e cobre o fluxo ponta a ponta "tentou
comentar sem login → foi para o login → voltou para a receita".
