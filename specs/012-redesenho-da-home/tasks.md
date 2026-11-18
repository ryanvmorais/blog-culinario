---
feature: Redesenho da home
status: concluído
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
- [x] Lighthouse da home (mobile e desktop) dentro dos limites de `.github/lighthouse/`; registrar o resultado. — RNF-05 (Lighthouse CI do PR: asserções aprovadas nas 5 páginas, 15 execuções por perfil)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 415 passed, 3 skipped; ruff/black/mypy verdes

## Adendo (2026-11-17): página da receita e listagem

> Status do adendo: aprovado (2026-11-17). Quebra o adendo do `design.md` (RF-19 a RF-28, RNF-07 a RNF-12,
> ADR-9 a ADR-13). As etapas continuam a numeração acima.

## Etapa 6 — Passos do modo de preparo

- [x] `receitas/models.py`: dataclass `TrechoDoPreparo` e `Receita.partes_do_preparo()`, com a regra de parágrafo numerado, a numeração pela posição e a `nota` depois do último passo; sem campo novo. — RF-22, RNF-07, ADR-9
- [x] `receitas/test_pagina_receita.py`: testes de unidade do método, sem banco ("1." e "1)", parágrafo antes, entre e depois dos passos, `start` do segundo grupo, `\r\n`, parágrafos vazios, receita sem passo). — RF-22, RF-28
- [x] `uv run python manage.py makemigrations --check --dry-run`: nenhuma migration. — RNF-07 (No changes detected)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 427 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 7 — Página da receita

- [x] `receitas/views.py`: `mais_receitas` no `ReceitaDetailView.get_context_data`, com `Case`/`When`, `select_related("categoria")` e corte em 3. — RF-24, RNF-08, ADR-10
- [x] `receitas/templates/receitas/detalhe.html`: ficha (`<dl>`), linha de autoria, etiquetas, `.receita-corpo` com o cartão de ingredientes (`tabindex="0"`) e o modo de preparo pelos trechos (`<p>`, `<ol class="passos" start>`, `.preparo-nota`, `linebreaksbr`). — RF-19, RF-20, RF-21, RF-22, ADR-12
- [x] `detalhe.html`: convite a comentar para anônimo, com e sem comentários, e o botão para o login com `?next=`; a seção de hoje para autenticado. — RF-23
- [x] `detalhe.html`: seção "Mais receitas" (`.rotulo` "Continue cozinhando", `h2`, `includes/cartao_receita.html`), ausente com a lista vazia. — RF-24, RNF-11
- [x] `static/css/base.css`: seção "4.2 Receita e listagem" com `.ficha`, `.receita-autoria`, `.receita-corpo`, `.ingredientes` (`sticky`, `max-height`, `overflow-y`), `.passos` (número em `::before` com `counter(list-item)`), `.preparo-nota`, `.convite-comentar` e a `@media (min-width: 900px)`; só tokens. — RF-19 a RF-23, RNF-09, ADR-12, ADR-13
- [x] `receitas/test_pagina_receita.py`: integração da página (ficha com plural e singular, "Autor removido", ingredientes sem linha vazia, `<ol>` e nota, convite por estado de login, "Mais receitas" com a mesma categoria primeiro, complemento, sem a aberta, limite de 3, ausência e `loading="lazy"`) e `assertNumQueries` com 2 e com 12 receitas. — RF-28, RNF-08
- [x] `receitas/tests.py`: ajustar ao HTML novo os testes do detalhe que procuravam o link "Entre" e a lista de ingredientes antiga, sem perder o que conferem. — RF-23, RF-20 (nenhum quebrou: conferem o conteúdo e o redirecionamento, não a marcação; o teste do aviso sem comentários em `nucleo/test_interface.py` foi o único ajustado)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 444 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 8 — Listagem

- [x] `receitas/views.py`: `categorias`, `total_publicadas` (soma das contagens) e `querystring_sem_categoria` no `ReceitaListView.get_context_data`; `paginate_by = 9` mantido. — RF-26, RF-27, ADR-11
- [x] `receitas/templates/receitas/lista.html`: busca `.busca-hero` com os campos ocultos de categoria e tag; `<nav class="lista-categorias" aria-label="Categorias">` com "Todas" e as pílulas, links sem `page` e com `q` e `tag`, `aria-current="page"` na ativa, ausente sem categorias. — RF-25, RF-26
- [x] `static/css/base.css`: `.lista-cabecalho .busca-hero` à esquerda, `.lista-categorias` e `.pilula[aria-current="page"]` com `--cor-primaria` e `--cor-texto-invertido`; remover o `.formulario-busca`, sem uso. — RF-25, RF-26, RNF-09
- [x] `receitas/test_listagem.py`: busca com os ocultos, pílulas na ordem com "Todas", contagens que ignoram a busca e a tag, `aria-current`, links que mantêm `q` e `tag` e voltam à primeira página, ausência sem categorias, soma igual ao `count()`, paginação com 9 e `assertNumQueries` com 2 e com 12 receitas. — RF-28, RNF-08
- [x] `nucleo/test_interface.py` e `nucleo/test_tema_escuro.py`: o token de borda de campo conferido na `.busca-hero`; `sticky` com `max-height` e `overflow-y`, o ponto de 900 px e a pílula marcada só com tokens; o contraste dos pares usados pela pílula marcada e pelo número do passo nos dois temas. — RNF-09, RF-28
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 462 passed, 3 skipped; ruff/black/mypy verdes (a listagem passou de 4 para 5 consultas, as pílulas; `test_listagem_nao_tem_n_mais_1_com_tags` atualizado)

## Etapa 9 — Catálogo, documentação e conferência

- [x] `docs/design-system.html`: ficha, cartão de ingredientes, passos numerados, convite a comentar e pílula marcada. — RNF-12
- [x] `CLAUDE.md`: o mapa de `receitas/` com os testes novos, se mudar o que ele descreve. — RNF-12
- [x] Navegador real, a 390 e a 1280 px, nos dois temas: axe-core sem violação e medidas de botão e alinhamento na receita e na listagem; o cartão de ingredientes fixo ao rolar e rolando por dentro com muitos ingredientes; registrar em "Notas de implementação do adendo" do `design.md`. — RNF-10, RF-21 (axe zerado em 12 combinações depois do desvio 1; cartão fixo a 88 px; nenhuma rolagem lateral)
- [x] Lighthouse da listagem e da receita (mobile e desktop) dentro dos limites de `.github/lighthouse/`; registrar o resultado. — RNF-11 — Lighthouse CI da `main` (9005e01): desktop 100 nas quatro notas; mobile 99 de desempenho e 100 nas outras três, LCP 2,1 s na listagem e 2,0 s na receita, CLS 0
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 462 passed, 3 skipped; ruff/black/mypy verdes

## Adendo 2 (2026-11-17): Entrar, Cadastro e páginas de erro

> Status do adendo 2: aprovado (2026-11-17). Quebra o adendo 2 do `design.md` (RF-29 a RF-33,
> RNF-13 a RNF-15, ADR-14 a ADR-16). As etapas continuam a numeração acima.

## Etapa 10 — Páginas de acesso

- [x] `usuarios/forms.py`: `AJUDA_SENHA`, rótulo "E-mail", ajuda da senha, rótulo "Confirme a senha" e confirmação sem ajuda. — RF-30, RF-31, ADR-15
- [x] `usuarios/templates/usuarios/campo.html`: rótulo sem dois-pontos, "(opcional)" no campo não obrigatório, ajuda com o id do `aria-describedby` e erros. — RF-30, ADR-14
- [x] `login.html` e `cadastro.html`: conteúdo no `.cartao-acesso`, campos pelo include e a frase de troca no `.cartao-acesso__troca`. — RF-29
- [x] `receitas/templates/receitas/detalhe.html`: rótulo do comentário sem dois-pontos. — RF-30
- [x] `static/css/base.css`: `.pagina-formulario` com o respiro do cartão, `.formulario__opcional`, `.cartao-acesso` e `.cartao-acesso__troca`, só com tokens; sai o `.pagina-formulario > p`. — RF-29, RF-30, RNF-13
- [x] `usuarios/test_paginas_de_acesso.py` e `nucleo/test_interface.py`: cartão, rótulos, frase da senha, validadores, senha recusada e o CSS do cartão. — RF-33
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 481 passed, 3 skipped; ruff/black/mypy verdes

## Etapa 11 — Páginas de erro, catálogo e conferência

- [x] `templates/erro.html` e `static/css/base.css`: `<body class="pagina-erro">` com a coluna flexível e o `<main>` que cresce. — RF-32, ADR-16
- [x] `nucleo/test_interface.py`: a classe nos cinco templates de erro e a regra de CSS. — RF-33
- [x] `docs/design-system.html`: cartão de acesso com "(opcional)" e a ajuda de senha. — RNF-15
- [x] `CLAUDE.md`: o mapa de `usuarios/` e as regras de interface do cartão, do campo e da frase de senha. — RNF-15
- [x] Navegador real, a 390 e 1280 px, nos dois temas: axe-core sem violação e medidas de desenho em Entrar, Cadastro e nas cinco páginas de erro; capturas a 360, 390, 430 e 1280 px contra o protótipo do `design.md`; registrar em "Notas de implementação do adendo 2" do `design.md`. — RNF-14 (axe zerado em 28 combinações; medidas sem achado)
- [x] Lighthouse de Entrar e Cadastro (mobile e desktop) dentro dos limites de `.github/lighthouse/`; registrar o resultado. — RNF-11 (Lighthouse CI do PR: asserções aprovadas nas 5 páginas, Entrar e Cadastro inclusive, em mobile e desktop)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 481 passed, 3 skipped; ruff/black/mypy verdes
