---
feature: Fundação do projeto (bootstrap)
status: concluído
data: 2026-09-12
relacionado: []
origem: engenharia reversa
---

# 000 — Fundação do projeto (bootstrap) — Tasks

> Registro retroativo (engenharia reversa) — tudo abaixo já estava
> concluído antes da spec 001 existir. Marcado `[x]` como histórico de
> construção, não como plano de execução.

## Etapa 1 — Planejamento

- [x] Fase de planejamento formal antes de qualquer código. — RF-01
- [x] Decisões tomadas com o mantenedor: idioma do código, abordagem de frontend, banco de dados, nome do repositório.
- [x] Plano escrito e aprovado cobrindo stack, arquitetura, estrutura de pastas, segurança e fluxo de trabalho.
- [x] Nome do repositório definido como `blog-culinario`, sem tecnologia — ADR-1.
- [x] Registro da decisão de deploy futuro no PythonAnywhere — ADR-5.

## Etapa 2 — Repositório GitHub

- [x] `gh repo create blog-culinario --public --source=. --remote=origin`.
- [x] `gh repo edit --delete-branch-on-merge`.
- [x] Secret scanning + secret scanning push protection ativados via API.
- [x] Private Vulnerability Reporting ativado via API.
- [x] `dependabot_security_updates` confirmado ativo (padrão do GitHub). — RF-05

## Etapa 3 — Projeto Python/Django

- [x] `uv init` + remoção do `main.py` padrão (projeto Django, não script).
- [x] `uv add django pillow django-environ whitenoise` (Django 6.1.1).
- [x] `uv add --dev pytest pytest-django ruff black mypy` (depois `django-stubs`, na spec 001).
- [x] `django-admin startproject blog_culinario .`.
- [x] `python manage.py startapp` para `nucleo`, `receitas`, `usuarios`.
- [x] Reorganização de `settings.py` em pacote `settings/` (`base.py`, `dev.py`, `prod.py`) — RF-03.
- [x] `manage.py`/`wsgi.py`/`asgi.py` apontando para `blog_culinario.settings.dev` por padrão.
- [x] `nucleo/views.py` (`home`), `nucleo/urls.py`, inclusão em `blog_culinario/urls.py` + serving de `media/` em `DEBUG`. — RF-02
- [x] Limpeza dos stubs padrão do `startapp` (imports não usados em `admin.py`/`models.py`/`tests.py`/`views.py` de `receitas`/`usuarios`).

## Etapa 4 — Design system e templates institucionais

- [x] `static/css/tokens.css`: paleta, tipografia (Fraunces/Inter), espaçamento, raio, sombra como custom properties.
- [x] `static/css/base.css`: reset, layout, navbar, hero, cartão de receita, botões, rodapé, responsivo mobile.
- [x] `static/js/interacoes.js`: menu mobile (vanilla, sem dependência). — RF-04, ADR-3
- [x] `templates/base.html` + `templates/includes/navbar.html`/`rodape.html`.
- [x] `nucleo/templates/nucleo/home.html`: hero + cartões de receita placeholder (substituídos por dados reais na spec 002).
- [x] Verificação visual via Playwright (desktop + mobile) antes de seguir. — Testes

## Etapa 5 — Documentação e configuração de projeto

- [x] `.gitignore` (Python, ambiente, caches, banco, estáticos/mídia gerados, segredos, editor/SO).
- [x] `.env.example` documentando `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`.
- [x] `.github/dependabot.yml` (uv + github-actions).
- [x] `.github/workflows/ci.yml` (ruff → black → mypy → pytest, mesma ordem local). — RF-06
- [x] `pyproject.toml`: seções `[tool.ruff]`, `[tool.black]`, `[tool.mypy]`, `[tool.pytest.ini_options]`.
- [x] `README.md` (modelo educacional: objetivo, guia de implementação, tecnologias, como rodar, atividades). — RF-07
- [x] `CONTRIBUTING.md` (modelo educacional, convite + diretrizes).
- [x] `LICENSE` (MIT).
- [x] `CLAUDE.md` (visão geral, comandos, arquitetura e convenções; aponta para `docs/` e `specs/` sem duplicar).

## Etapa 6 — Stack documentada

- [x] `docs/stack.md`: cada peça com o que faz, por que foi escolhida, o que estudar, e a seção "o que não está na stack". — RF-08

## Etapa 7 — Verificação e commit inicial

- [x] Portão de qualidade: `ruff check` + `black --check` + `mypy` + `python manage.py check` — verdes.
- [x] Commit único direto na `main` (`chore: estrutura inicial do projeto Django`) — ADR-4.
- [x] `git push -u origin main`.
