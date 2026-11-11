---
feature: Busca textual e filtros por categoria/tag
status: concluído
date: 2026-09-12
related:
  - 002-listagem-detalhe-receitas/requirements.md
origin: concepcao
---

# 003 — Busca textual e filtros por categoria/tag — Tasks

## Etapa 1 — Filtros na view

- [x] `receitas/views.py`: `get_queryset()` ganha os filtros `q` (título/ingredientes via `Q(...) | Q(...)`), `categoria` (`categoria__slug`) e `tag` (`tags__slug`), cada um aplicado só quando o parâmetro está presente. — RF-01, RF-02, RF-03, RF-04, RNF-01, RNF-02, ADR-1, ADR-2
- [x] `receitas/views.py`: `get_context_data()` novo, expondo `termo_busca`, `categoria_selecionada`, `tag_selecionada` e `querystring` (GET sem `page`, urlencoded). — RF-06, RF-07, ADR-3
- [x] Portão de qualidade parcial: `uv run ruff check . && uv run black --check . && uv run mypy .` — verdes.

## Etapa 2 — Formulário de busca e estado vazio

- [x] `receitas/templates/receitas/lista.html`: formulário `GET` com `<label>` + `<input name="q">`, hidden inputs para `categoria_selecionada`/`tag_selecionada` quando ativos, botão de busca. — RF-01, RF-07, ADR-3
- [x] `receitas/templates/receitas/lista.html`: mensagem de estado vazio citando `termo_busca` quando houver, com link para `receitas:lista` sem parâmetros. — RF-05
- [x] `static/css/base.css`: classe `.formulario-busca` (layout do input + botão).
- [x] Portão de qualidade parcial: verdes.

## Etapa 3 — Categoria/tag clicáveis e paginação com filtro

- [x] `templates/includes/cartao_receita.html`: categoria vira `<a href="{% url 'receitas:lista' %}?categoria=...">`. — RF-02
- [x] `receitas/templates/receitas/detalhe.html`: categoria e cada etiqueta de tag viram `<a href="...">`; `static/css/base.css`: `.etiqueta` ganha `text-decoration: none`. — RF-02, RF-03
- [x] `templates/includes/paginacao.html`: links de anterior/próxima apendam `&{{ querystring }}` quando não vazio. — RF-06
- [x] Portão de qualidade parcial: verdes.

## Etapa 4 — Testes

- [x] `receitas/tests.py`: régua nova "Busca e filtros" — busca por título, busca por ingrediente, termo ausente, categoria existente/inexistente, tag existente/inexistente, combinação busca+categoria (interseção), estado vazio com a mensagem citando o termo, paginação preservando `?categoria=...` no HTML renderizado. — RF-01 a RF-06, RNF-02
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **32 passed**; ruff/black/mypy limpos; `manage.py check` sem issues.
- [x] Verificação visual manual (formulário de busca, resultado de busca, estado vazio com link "Ver todas as receitas", filtro por tag clicado a partir do detalhe) — screenshots conferidos.

### Correção feita durante a implementação

O primeiro teste de combinação busca+categoria (`test_busca_e_categoria_combinam_com_e_logico`)
falhou na primeira execução: o builder `_receita()` tem "cenoura" no
`ingredientes` default, então uma receita de controle ("Bolo de chocolate")
também batia na busca por "cenoura" sem eu ter notado. Corrigido
sobrescrevendo `ingredientes` explicitamente nas receitas de controle do
teste — não é um bug do código de produção, só do dado de teste.
