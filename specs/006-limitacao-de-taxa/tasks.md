---
feature: Limitação de taxa em login e comentários
status: concluído
date: 2026-09-12
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
  - 011-hospedagem/requirements.md
origin: concepcao
---

# 006 — Limitação de taxa em login e comentários — Tasks

## Etapa 1 — Módulo de limitação de taxa

- [x] `blog_culinario/limitacao.py` (novo arquivo): função `limite_excedido(request, chave, limite, janela_segundos) -> bool`, usando `cache.add()` + `cache.incr()` do backend de cache padrão do Django. — RF-01, RF-02, RF-03, RNF-01, RNF-02, ADR-1, ADR-2, ADR-3
- [x] Portão de qualidade parcial: `ruff check` + `black --check` + `mypy` verdes.

## Etapa 2 — Aplicar no login

- [x] `usuarios/views.py`: `EntrarView.post()` chama `limite_excedido(request, "login", limite=5, janela_segundos=300)`; bloqueado → `messages.error` + redirect para `usuarios:entrar` sem chamar `super().post()`. — RF-01
- [x] Portão de qualidade parcial: verdes (`manage.py check` também).

## Etapa 3 — Aplicar na criação de comentário

- [x] `receitas/views.py`: `ComentarioCreateView.post()` chama `limite_excedido(request, "comentario", limite=5, janela_segundos=60)` antes do `get_object_or_404`; bloqueado → `messages.error` + o mesmo redirect com `#comentarios` já usado no fluxo de erro de validação. — RF-02
- [x] Portão de qualidade parcial: verdes.

## Etapa 4 — Testes

- [x] `usuarios/tests.py`: `cache.clear()` isolando os testes; 5 tentativas de login incorretas seguidas de uma 6ª bloqueada com a mensagem de limite (sem tocar o `AuthenticationForm`); dois IPs (`REMOTE_ADDR` diferente) não compartilham o contador; expiração da janela testada diretamente em `limite_excedido()` (janela curta + `time.sleep`, já que a janela real do login é longa demais para esperar num teste). — RF-01, RF-03
- [x] `receitas/tests.py`: mesmo padrão para comentário — 5 criados seguidos de um 6º bloqueado (não persiste no banco); dois IPs não compartilham o contador. — RF-02, RF-03
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **62 passed**; `manage.py check` sem issues.

### Correção feita durante a implementação

Um teste falhou por bug do próprio teste (faltava `follow=True` no POST bloqueado
para capturar a mensagem de erro no redirect) — corrigido em
`test_login_bloqueia_a_partir_da_sexta_tentativa_no_mesmo_ip`.

Também apareceu uma falha pré-existente e não relacionada a esta spec:
`nucleo/tests.py::test_home_mostra_receitas_publicadas_recentes` quebrou
porque o Prettier havia reformatado `nucleo/templates/nucleo/home.html`
e partido a tag `{% include "includes/cartao_receita.html" %}`
em duas linhas — o lexer de template do Django não reconhece uma tag
`{% ... %}` com quebra de linha no meio (regex sem `DOTALL`). Corrigido em
duas partes: `.prettierignore` na raiz do projeto para o Prettier nunca mais
tocar `templates/`, e a tag quebrada voltou para uma linha só.

## Adendo (2026-11-16): login do Admin, cadastro e IPv6

> Status do adendo: concluído (2026-11-16). Quebra o adendo do `design.md` (RF-04 a RF-08, RNF-03 a
> RNF-05, ADR-5 a ADR-8). As etapas continuam a numeração acima.

## Etapa 5 — Chave por rede e teto do cache

- [x] `blog_culinario/limitacao.py`: função privada `_identificador_de_rede(ip)` (IPv4 normalizado, IPv4 dentro do IPv6, /64 no IPv6, texto que não é IP como está) e a chave `limite:<namespace>:<identificador de rede>` no `limite_excedido()`. — RF-06, ADR-6, ADR-7
- [x] `blog_culinario/limitacao.py`: constantes `LIMITE_LOGIN`, `JANELA_LOGIN_SEGUNDOS` e `MENSAGEM_LIMITE_LOGIN`; `usuarios/views.py::EntrarView.post()` passa a usá-las, sem mudar o comportamento. — RF-04, RNF-04
- [x] `blog_culinario/settings/base.py`: `"OPTIONS": {"MAX_ENTRIES": 10_000}` no `CACHES["default"]`. — RF-07, ADR-8
- [x] `nucleo/test_limitacao.py` (novo): unidade do `_identificador_de_rede()`; dois `REMOTE_ADDR` do mesmo /64 dividem o contador do login e de /64 diferentes, não; um contador no limite continua recusando depois de 400 contadores de outros IPs. — RF-06, RF-07, RF-08
- [x] Portão de qualidade: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — 332 passed, 3 skipped; ruff/black/mypy verdes. O teste do sitemap falhou à parte (ver "Correção feita durante o adendo").

## Etapa 6 — Login do Admin

- [x] `blog_culinario/site_admin.py` (novo): `SiteAdminComLimite(AdminSite)` com o `login()` limitado no POST (mensagem e redirect para `request.get_full_path()`), e `ConfigAdmin(AdminConfig)` com o `default_site`. — RF-04, RNF-05, ADR-5
- [x] `blog_culinario/settings/base.py`: `"django.contrib.admin"` vira `"blog_culinario.site_admin.ConfigAdmin"` no `INSTALLED_APPS`. — RF-04, ADR-5
- [x] `nucleo/test_limitacao.py`: sexto POST errado no `reverse("admin:login")` recusado sem autenticar e com a mensagem; staff abaixo do limite entra; o limite esgotado numa tela de login vale na outra; o GET não soma; `admin.site` é um `SiteAdminComLimite`; um `ROOT_URLCONF` de teste com o Admin em outro caminho mantém o limite. — RF-04, RF-08
- [x] Portão de qualidade: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest`; `uv run python manage.py check` sem issues — 340 passed, 3 skipped; ruff/black/mypy verdes; `check` sem issues.

## Etapa 7 — Cadastro

- [x] `usuarios/views.py`: `CadastroView.post()` com `limite_excedido(request, "cadastro", limite=10, janela_segundos=3600)` antes do `super().post()`; acima do limite, `messages.error` com a mensagem do RF-05 e redirect para `usuarios:cadastro`. — RF-05
- [x] `usuarios/tests.py`: o 11º envio recusado sem criar o usuário, com o modo demonstração ligado e desligado; o contador do cadastro esgotado não recusa o login. — RF-05, RF-08
- [x] Portão de qualidade: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — 343 passed, 3 skipped; ruff/black/mypy verdes.

## Etapa 8 — Specs e documentação

- [x] `specs/011-hospedagem/requirements.md`: a decisão resolvida 10 ganha a linha `**Superseded by** 006-limitacao-de-taxa, adendo, decisão resolvida 1.`; `specs/006-limitacao-de-taxa/requirements.md`: o não-objetivo "admin" ganha a mesma referência. — RF-04
- [x] `CLAUDE.md`: a linha do `limitacao.py` no mapa da arquitetura cita login, Admin, cadastro e comentário, e o `site_admin.py` entra no mapa. — RF-04, RF-05
- [x] `README.md` e `README.en.md`: a frase da limitação de taxa (seções de autenticação e de segurança) cita o Admin e o cadastro, nas duas línguas. — RF-04, RF-05
- [x] `specs/006-limitacao-de-taxa/` e `specs/README.md`: status `concluído` nos três arquivos e no roadmap. — RF-08
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — 344 passed, 3 skipped; ruff/black/mypy verdes, com o teste do sitemap corrigido.

### Correção feita durante o adendo

O teste `nucleo/test_descoberta.py::test_sitemap_lista_home_lista_e_so_receitas_publicadas`
falhava das 21h à meia-noite de Brasília (nos portões das etapas 5 a 7), também na `main`,
sem relação com o adendo: ele
comparava o `lastmod` do sitemap com o `atualizado_em` em UTC, e o template do sitemap
escreve a data no fuso do site (`TIME_ZONE`). Corrigido no próprio teste, que passou a
comparar com `timezone.localdate()`.
