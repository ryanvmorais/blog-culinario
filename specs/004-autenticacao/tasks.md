---
feature: Autenticação de usuários (cadastro, login, logout)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 004 — Autenticação de usuários — Tasks

## Etapa 1 — Infraestrutura (settings e rotas)

- [x] `blog_culinario/settings/base.py`: `LOGIN_URL = "usuarios:entrar"`, `LOGIN_REDIRECT_URL = "nucleo:home"`, `LOGOUT_REDIRECT_URL = "nucleo:home"`.
- [x] `usuarios/urls.py`: `app_name = "usuarios"`, rotas `cadastro/`, `entrar/`, `sair/`.
- [x] `blog_culinario/urls.py`: `path("usuarios/", include("usuarios.urls"))`.

## Etapa 2 — Form e views

- [x] `usuarios/forms.py`: `FormularioCadastro` (`UserCreationForm` + `email` opcional). — RF-01
- [x] `usuarios/views.py`: `CadastroView` (`FormView`, autentica após criar — ADR-1). — RF-01, RF-06
- [x] `usuarios/views.py`: `EntrarView` (`LoginView` + mensagem de boas-vindas). — RF-02, RF-05, RF-06, RNF-01
- [x] `usuarios/views.py`: `SairView` (`LogoutView` via POST — ADR-2 — + mensagem de despedida). — RF-03, RF-06
- [x] Portão de qualidade parcial (etapas 1+2 juntas, urls.py dependia de views.py existir): `uv run ruff check . && uv run black --check . && uv run mypy . && uv run python manage.py check` — verdes.

## Etapa 3 — Templates: cadastro, login, mensagens e navbar

- [x] `usuarios/templates/usuarios/cadastro.html`: formulário com `{% csrf_token %}`, campos rotulados.
- [x] `usuarios/templates/usuarios/login.html`: formulário com `{% csrf_token %}` e campo oculto `next`.
- [x] `templates/includes/mensagens.html`: itera `messages`, classe `mensagem--{{ message.tags }}`; incluído em `base.html` logo após a navbar. — RF-06, ADR-3
- [x] `templates/includes/navbar.html`: bloco `{% if user.is_authenticated %}` (saudação + form POST de logout) / `{% else %}` (Entrar/Cadastrar). — RF-04
- [x] `static/css/base.css`: nova seção 8 com `.formulario` (cadastro/login), `.link-botao` (botão de logout com cara de link) e `.mensagens`/`.mensagem--*`.
- [x] Portão de qualidade parcial: verdes.

## Etapa 4 — Testes

- [x] `usuarios/tests.py`: cadastro com dados válidos autentica e cria a conta; username duplicado, senha fraca e senhas divergentes cada um falha sem criar conta. — RF-01
- [x] `usuarios/tests.py`: login com credenciais corretas autentica; credenciais erradas mostram mensagem genérica. — RF-02
- [x] `usuarios/tests.py`: logout (POST) encerra a sessão; GET em `/usuarios/sair/` não desloga (405, comportamento padrão do `LogoutView`). — RF-03, ADR-2
- [x] `usuarios/tests.py`: HTML da navbar via `client.get("/")` contém "Entrar" anônimo e `username`/"Sair" autenticado. — RF-04
- [x] `usuarios/tests.py`: POST em `usuarios:entrar?next=/receitas/` com login válido redireciona para `/receitas/`. — RF-05
- [x] `usuarios/tests.py`: resposta de cadastro/login/logout contém a mensagem esperada. — RF-06
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **43 passed**; ruff/black/mypy limpos.
- [x] Verificação visual manual (cadastro, autenticação automática, logout, erro genérico de login) — screenshots conferidos.
