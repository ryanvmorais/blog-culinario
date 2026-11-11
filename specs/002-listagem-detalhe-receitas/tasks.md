---
feature: Listagem e detalhe público de receitas
status: concluído
date: 2026-09-12
related:
  - 001-modelagem-receitas/requirements.md
origin: concepcao
---

# 002 — Listagem e detalhe público de receitas — Tasks

## Etapa 1 — Views e URLs

- [x] `receitas/views.py`: `ReceitaListView` (`ListView`, `paginate_by = 9`, `get_queryset()` com `publicado=True` + `select_related`/`prefetch_related`), com docstring explicando o que o override faz. — RF-01, RF-02, RNF-01, ADR-1
- [x] `receitas/views.py`: `ReceitaDetailView` (`DetailView`, mesma queryset filtrada/otimizada). — RF-03, RF-04, RNF-01, ADR-1
- [x] `receitas/urls.py`: `app_name = "receitas"`, rota `""` -> `lista`, `"<slug:slug>/"` -> `detalhe`.
- [x] `blog_culinario/urls.py`: `path("receitas/", include("receitas.urls"))`.
- [x] Portão de qualidade parcial: `uv run ruff check . && uv run black --check . && uv run mypy .` — todos verdes.

## Etapa 2 — Templates e includes compartilhados

- [x] `templates/includes/cartao_receita.html`: recebe `receita`; `<img>` quando há `imagem_capa`, placeholder quando não há. — ADR-3
- [x] `templates/includes/paginacao.html`: anterior/próxima a partir de `page_obj`, com `.botao--contorno`. — RF-02
- [x] `receitas/templates/receitas/lista.html`: `extends base.html`, itera `receitas` com o include do cartão, inclui a paginação, define `titulo`/`descricao` (RNF-02). — RF-01, RF-02
- [x] `receitas/templates/receitas/detalhe.html`: todos os campos do model; `receita.ingredientes.splitlines` numa lista; `receita.modo_de_preparo|linebreaks`; `receita.autor.username` com fallback "Autor removido" quando `None`. — RF-03
- [x] Portão de qualidade parcial.

### Correção feita durante a implementação

O design previa "CSS sem mudança", mas a paginação, o cabeçalho da listagem
e o layout do detalhe (capa maior, meta-informação, etiquetas de tag)
precisavam de classes que não existiam ainda. Adicionadas em
`static/css/base.css` como nova seção 6 ("Página de detalhe de receita") +
duas classes em Layout (`.cabecalho-pagina`, `.paginacao`) — reaproveitando
os tokens existentes, sem introduzir cor/tamanho novo.

## Etapa 3 — Navegação real

- [x] `templates/includes/navbar.html`: link "Receitas" para `{% url 'receitas:lista' %}`. — RF-05
- [x] `nucleo/templates/nucleo/home.html`: botão "Ver receitas" do hero para `{% url 'receitas:lista' %}`. — RF-05

## Etapa 4 — Home com receitas reais

- [x] `nucleo/views.py`: `home()` consulta as 3 receitas publicadas mais recentes (`select_related("categoria")`, sem `tags`) e envia `receitas_recentes` no contexto. — RF-06
- [x] `nucleo/templates/nucleo/home.html`: troca os 3 cartões estáticos por `{% for receita in receitas_recentes %}` com o include; estado vazio "em breve" quando a lista estiver vazia. — RF-06
- [x] Portão de qualidade parcial: `uv run ruff check . && uv run black --check . && uv run mypy .` — verdes (precisou `black .` reformatar `nucleo/views.py`).

## Etapa 5 — Testes

- [x] `receitas/tests.py`: réguas novas — listagem (só publicadas aparecem, ordenação, paginação, 404 em página inexistente, `assertNumQueries` fixado no valor medido: 3). — RF-01, RF-02, RNF-01
- [x] `receitas/tests.py`: detalhe (200 para publicada, 404 para não publicada e para slug inexistente, autor `None` não quebra a página). — RF-03, RF-04
- [x] `nucleo/tests.py`: home com receita publicada mostra o título dela; sem nenhuma publicada mostra a mensagem de "em breve". — RF-06
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **22 passed**; ruff/black/mypy limpos; `manage.py check` sem issues.
- [x] Verificação visual manual no navegador (home, listagem com 4 receitas, detalhe com tags/ingredientes/modo de preparo) — screenshots conferidos, sem regressão de design.
