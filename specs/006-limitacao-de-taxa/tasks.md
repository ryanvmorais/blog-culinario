---
feature: Limitação de taxa em login e comentários
status: concluído
date: 2026-09-12
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
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
