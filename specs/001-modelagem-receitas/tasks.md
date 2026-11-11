---
feature: Modelagem de domínio das receitas (Categoria, Receita, Tag)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 001 — Modelagem de domínio das receitas — Tasks

## Etapa 1 — Helper de slug compartilhado

- [x] `receitas/utils.py`: criar `gerar_slug_unico(modelo, texto, campo_slug="slug")`, com docstring completa (Args/Returns). — RF-01, RF-02, ADR-1

## Etapa 2 — Categoria e Tag

- [x] `receitas/models.py`: model `Categoria` (`nome`, `slug`, `Meta`, `__str__`, `save()` chamando o helper da Etapa 1 quando `slug` estiver vazio). — RF-01
- [x] `receitas/models.py`: model `Tag`, mesmo padrão de `Categoria`. — RF-02

## Etapa 3 — Receita

- [x] `receitas/models.py`: função `validar_tamanho_imagem(arquivo)` (rejeita acima de 5 MB). — RF-04
- [x] `receitas/models.py`: model `Receita` com todos os campos do design (`titulo` até `atualizado_em`), `categoria` com `on_delete=PROTECT`, `tags` M2M, `autor` com `on_delete=SET_NULL, null=True, blank=True`, `imagem_capa` com `FileExtensionValidator` + `validar_tamanho_imagem`, `save()` gerando slug. — RF-03, RF-04, ADR-2, ADR-3
- [x] `uv run python manage.py makemigrations receitas` — conferir que gera **uma única** `0001_initial.py`. — RNF-03
- [x] `uv run python manage.py migrate` — aplicar localmente, sem erro.

## Etapa 4 — Admin

- [x] `receitas/admin.py`: `CategoriaAdmin` e `TagAdmin` (`list_display`, `search_fields`, `prepopulated_fields = {"slug": ("nome",)}`). — RF-05
- [x] `receitas/admin.py`: `ReceitaAdmin` (`list_display`, `list_filter`, `search_fields`, `prepopulated_fields = {"slug": ("titulo",)}`, `autocomplete_fields = ["categoria", "autor"]`, `list_select_related = ["categoria", "autor"]`). — RF-05, RNF-02
- [x] Portão de qualidade parcial: `uv run ruff check . && uv run black --check . && uv run mypy .` — todos verdes (foi preciso ignorar `RUF012` no `pyproject.toml` para `ModelAdmin`/`Meta`, e usar `Any` + `# type: ignore[attr-defined]` pontual no helper de slug genérico).

## Etapa 5 — Testes

- [x] `receitas/tests.py`: docstring de módulo com a estratégia de isolamento (banco de teste via `pytest-django`, sem mocks — os três models são puro ORM) + builders `_categoria`/`_tag`/`_receita` com `Args`/`Returns` completos.
- [x] Testes de slug único: criar duas `Categoria`/`Tag` com o mesmo nome, conferir slugs `x` e `x-2`. — RF-01, RF-02
- [x] Testes de `Receita`: defaults (`publicado=False`, timestamps), exclusão de `categoria` em uso levanta `ProtectedError`, exclusão de `tag` não afeta a receita, exclusão de `autor` deixa `autor=None` na receita. — RF-03, RNF-01
- [x] Testes de validação de `imagem_capa`: arquivo > 5 MB e extensão inválida levantam `ValidationError` em `full_clean()`; receita sem imagem continua válida. — RF-04
- [x] Testes smoke do admin: usuário staff recebe 200 em `/admin/receitas/categoria/`, `/admin/receitas/tag/`, `/admin/receitas/receita/`. — RF-05
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **11 passed**; ruff/black/mypy limpos; `manage.py check` sem issues.

### Correções feitas durante a implementação

- `Categoria.nome`/`Tag.nome` tinham `unique=True` no design, o que tornaria
  o cenário de RF-01/RF-02 (duas categorias com o mesmo nome) impossível de
  testar — a unicidade real é do `slug`. Campo `nome` corrigido para não ser
  único; `design.md` atualizado para refletir isso.
- `MAILERS` (não `EMAIL_BACKEND`, deprecado no Django 6.1) movido para
  `settings/base.py` como default de console — não fazia parte do escopo da
  spec, mas apareceu como warning de depreciação ao rodar os testes.
