---
feature: Redesenho da home
status: em andamento
date: 2026-11-17
related:
  - 002-listagem-detalhe-receitas/requirements.md
  - 003-busca-e-filtros/requirements.md
  - 008-correcoes-de-interface/requirements.md
origin: concepcao
---

# 012 — Redesenho da home — Tasks

## Etapa 1 — Consultas e view

- [x] `specs/README.md`: linha da 012 no roadmap, com o status da spec. — RNF-06
- [x] `receitas/models.py`: `CategoriaQuerySet.com_receitas_publicadas()` (anota `total_receitas`, descarta zero, ordena pela contagem e pelo nome) e `objects = CategoriaQuerySet.as_manager()`; conferir que `makemigrations --check` não gera migration. — RF-06, RF-12, RNF-01, ADR-2
- [x] `nucleo/views.py`: `home` com `destaque`, `recentes`, `total_receitas`, `categorias` e `total_comentarios` (uma consulta para as 4 mais recentes). — RF-01, RF-03, RF-05, RF-06, RF-07, ADR-1
- [x] `nucleo/templatetags/navegacao.py`: `{% link_repositorio %}` (arquivo em `blob/main`, pasta em `tree/main`, base no `URL_REPOSITORIO`) e a inclusion tag `{% categorias_do_rodape %}` com `templates/includes/rodape_categorias.html`. — RF-09, RF-12, ADR-3, ADR-8
- [x] `receitas/tests.py`: o método do `QuerySet` (contagem só de publicadas, categoria vazia fora, ordem no empate). — RF-06
- [x] `nucleo/test_home.py`: contexto da view (destaque, recentes sem repetir, contagens com aprovados e publicados) e o mesmo número de consultas com 1 e com 10 receitas. — RF-03, RF-05, RF-07, RNF-02
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 375 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 2 — Home

- [x] `static/css/base.css`: `.hero-dividido` (duas colunas acima de 720 px; uma coluna centrada até 720 px e com `--uma-coluna`), `.busca-hero`, `.numeros`, `.hero__conta`, `.rotulo`, `.pilula`, `.destaque`, `.notas-codigo`, `.secao` e o cartão de mesma altura (`flex`, meta com `margin-top: auto`). — RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-08, RF-09, RF-11
- [x] `nucleo/templates/nucleo/home.html`: abertura (legenda, `h1`, descrição, busca, números com `pluralize`, convite só sem login, destaque com a capa sem `loading="lazy"`), categorias, recentes com "Ver todas as N receitas" e estado vazio, "Por dentro" com as quatro notas e `{% link_repositorio %}`. — RF-01 a RF-07, RF-09, RF-11, RNF-05
- [x] `nucleo/test_home.py`: HTML da home (colunas, busca, números com plural, singular e zero, convite, destaque com um link, pílulas com contagem, ordem e link de filtro, recentes, botão, estados com 0 e 1 receita, rótulos fora do `h2`, títulos sem pulo de nível) e os caminhos do "Por dentro" existindo no repositório. — RF-01 a RF-07, RF-09, RF-10, RF-11, RF-18, RNF-04
- [x] `nucleo/tests.py` e `nucleo/test_interface.py`: atualizar os testes da home das specs 002 e 008 (destaque mais 3, convite no lugar do botão, "Por dentro" novo) e acrescentar o CSS do cartão de mesma altura. — RF-04, RF-07, RF-08
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 394 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 3 — Rodapé

- [x] `templates/includes/rodape.html`: marca e frase, "Navegar" (Entrar e Cadastrar só sem login), "Categorias" por `{% categorias_do_rodape %}`, "O projeto" (`URL_REPOSITORIO`, `docs/stack.md`, `SECURITY.md`, `LICENSE`), cada coluna num `<nav aria-labelledby>`, e o "©" centrado. — RF-12, ADR-3
- [x] `static/css/base.css`: grade do rodapé (quatro colunas; até 720 px, marca na largura toda e links em duas colunas) e `.rodape__base` centrado. — RF-12
- [x] `nucleo/test_menu_e_rodape.py`: colunas, regiões com nome, links do projeto, categorias na ordem, Entrar e Cadastrar só sem login, "©" centrado; as páginas de erro sem as categorias e sem consulta ao banco. — RF-12, RF-13, RF-18
- [x] `nucleo/test_descoberta.py`: ajustar o que conferir a frase antiga do rodapé, se for o caso. — RF-12 (nada a ajustar: o teste confere a `description`, não o rodapé)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 403 passed, 3 skipped; ruff/black/mypy verdes (o teste de N+1 da listagem passou a contar a consulta do rodapé, ADR-3)

## Etapa 4 — Menu do celular

- [x] `static/css/tokens.css`: `--altura-barra` e `--cor-veu`, com o par do véu no tema escuro. — RF-14, RNF-03, ADR-5
- [x] `templates/includes/navbar.html`: marcação única (`navbar__painel` com links e `navbar__conta`), o rótulo "Sua conta", os dois SVG no botão, `aria-current="page"` pela rota e o véu com `hidden`. — RF-14, RF-15, RF-16, ADR-4, ADR-7
- [x] `static/css/base.css`: barra acima de 720 px como hoje; até 720 px, painel `fixed` da barra ao fim da tela, 80% da largura, `transform` e `visibility`, links de 48 px, conta com aparência de botão, véu, ícone pelo `aria-expanded`, botão de 48 x 48 px, `html.menu-aberto` sem rolagem; o painel no bloco de movimento reduzido. — RF-14, RF-15, RF-16, RF-17, ADR-5, ADR-7
- [x] `static/js/interacoes.js`: véu, `inert` em `<main>`, mensagens e rodapé, classe `menu-aberto`, fechar pelo véu e por link sem devolver o foco, fechar ao passar de 720 px. — RF-14, RF-17, ADR-6
- [x] `nucleo/test_menu_e_rodape.py` e `nucleo/test_interface.py`: o botão (nome, `aria-expanded`, os dois ícones), `aria-current`, o grupo "Sua conta" com e sem login, o véu, o `inert` e o `hidden` no JS, o `transform` e o movimento reduzido no CSS; o teste do menu da spec 008 ajustado. — RF-14 a RF-17, RF-18 (o da spec 008 seguiu passando sem ajuste)
- [x] `nucleo/test_tema_escuro.py`: o `--cor-veu` com par no tema escuro. — RNF-03
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 415 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 5 — Catálogo, documentação e conferência

- [x] `docs/design-system.html`: pílula, rótulo, cartão em destaque, nota de código, rodapé em colunas e painel do menu aberto. — RNF-06
- [x] `specs/002-listagem-detalhe-receitas/requirements.md` e `specs/008-correcoes-de-interface/requirements.md`: a linha `**Superseded by** 012-redesenho-da-home, RF-07.` (002, RF-06) e `… RF-04.` (008, RF-01). — RF-04, RF-07
- [x] `CLAUDE.md`: o mapa de `nucleo/` com a `templatetags/navegacao.py` e os testes novos. — RNF-06
- [x] Navegador real, a 390 e a 1280 px, nos dois temas, com o menu aberto e fechado: axe-core sem violação, medidas de botão e alinhamento, primeira tela da home; registrar em "Notas de implementação" do `design.md`. — RNF-04 (axe zerado em 14 combinações; medidas sem achado)
- [ ] Lighthouse da home (mobile e desktop) dentro dos limites de `.github/lighthouse/`; registrar o resultado. — RNF-05
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 415 passed, 3 skipped; ruff/black/mypy verdes
