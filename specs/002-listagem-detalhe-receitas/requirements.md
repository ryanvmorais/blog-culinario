---
feature: Listagem e detalhe público de receitas
status: concluído
date: 2026-09-12
related:
  - 001-modelagem-receitas/requirements.md
origin: concepcao
---

# 002 — Listagem e detalhe público de receitas

## Contexto e problema

A spec 001 modelou `Categoria`, `Tag` e `Receita`, mas não existe nenhuma
página pública que consuma esses dados — a home hoje mostra cartões de
receita estáticos (placeholder) só para validar o design system, e o link
"Receitas" da navbar ainda não existe (spec 001 o adiou de propósito). Esta
spec conecta o domínio às páginas públicas: listagem paginada e detalhe.

## Objetivos

- Listagem pública em `/receitas/`, só com receitas publicadas, paginada.
- Página de detalhe em `/receitas/<slug>/`, com todos os campos do model.
- Ligar a navegação real (navbar, hero da home) a essas páginas.
- Substituir os cartões placeholder da home pelas receitas reais mais
  recentes.

## Não-objetivos

- Busca textual (spec futura).
- Filtro por categoria ou por tag na listagem (spec futura — junto da
  busca, para não fragmentar a navegação por conteúdo em duas specs).
- Comentários (depende de `usuarios`, spec futura).
- Qualquer interação via AJAX/infinite scroll — paginação é só link
  "anterior/próxima" com reload de página, no mesmo espírito "sem build
  step" do restante do frontend.

## Personas

- Como **leitor anônimo**, quero navegar pelas receitas publicadas e abrir
  uma para ver o preparo completo, sem precisar de conta.
- Como **administrador**, quero que uma receita que eu deixei como rascunho
  (`publicado=False`) não apareça em lugar nenhum do site público.

## Requisitos funcionais

### RF-01 — Listagem pública

- **Given** existem receitas publicadas e não publicadas no banco
  **When** um visitante acessa `/receitas/`
  **Then** só as receitas com `publicado=True` aparecem, ordenadas da mais
  recente para a mais antiga, cada uma renderizada com o componente
  `.cartao-receita` já existente no design system (`static/css/base.css`).

### RF-02 — Paginação

- **Given** existem mais de 9 receitas publicadas
  **When** o visitante acessa `/receitas/` sem parâmetro de página
  **Then** as 9 mais recentes aparecem, com um controle "anterior/próxima"
  no rodapé da listagem.
- **Given** o visitante está na primeira página
  **When** a listagem renderiza
  **Then** o controle "anterior" não aparece (ou aparece desabilitado).
- **Given** o visitante acessa `/receitas/?page=2`
  **When** existe uma segunda página
  **Then** o conjunto seguinte de receitas é exibido.
- **Given** o visitante acessa uma página que não existe (ex.: `?page=999`)
  **When** a listagem processa o parâmetro
  **Then** a resposta é 404 (comportamento padrão do `Paginator` do Django).

### RF-03 — Página de detalhe

- **Given** uma receita publicada com slug `bolo-de-cenoura`
  **When** um visitante acessa `/receitas/bolo-de-cenoura/`
  **Then** a página exibe: título, imagem de capa (ou um estado visual sem
  imagem, se `imagem_capa` estiver vazio), resumo, tempo de preparo,
  porções, categoria, tags, lista de ingredientes, modo de preparo e o
  nome do autor.
- **Given** a receita não tem autor (`autor=None`, ex.: usuário removido)
  **When** a página de detalhe renderiza
  **Then** exibe "Autor removido" no lugar do nome, sem quebrar a página.

### RF-04 — Receita inexistente ou não publicada retorna 404

- **Given** um slug que não corresponde a nenhuma receita
  **When** um visitante acessa `/receitas/<slug-invalido>/`
  **Then** a resposta é 404.
- **Given** um slug que existe mas pertence a uma receita com
  `publicado=False`
  **When** um visitante anônimo acessa essa URL
  **Then** a resposta também é 404 — rascunho não vaza por URL direta.

### RF-05 — Navegação real

- **Given** as páginas de listagem e detalhe existem
  **When** um visitante clica em "Receitas" na navbar, ou no botão
  "Ver receitas" do hero da home
  **Then** é levado para `/receitas/` (em vez do anchor `#receitas-em-breve`
  usado como placeholder na spec anterior).

### RF-06 — Home exibe receitas reais

- **Given** existem receitas publicadas
  **When** a home (`/`) carrega
  **Then** a seção que hoje mostra 3 cartões estáticos passa a mostrar até
  3 receitas publicadas reais, mais recentes primeiro, cada uma linkando
  para sua página de detalhe.
- **Given** ainda não existe nenhuma receita publicada
  **When** a home carrega
  **Then** a seção exibe uma mensagem simples de "em breve" em vez de um
  grid vazio ou de cartões com dado inexistente.

## Requisitos não-funcionais

### RNF-01 — Sem N+1 nas views públicas

Listagem e detalhe devem usar `select_related("categoria", "autor")` e, na
listagem, `prefetch_related("tags")` — o volume de receitas vai crescer e a
query não pode escalar linearmente com o número de tags por card.

### RNF-02 — Metadados de página por rota

Cada página define `<title>` e `<meta description>` próprios via os blocks
já existentes em `templates/base.html` (`titulo`, `descricao`) — a listagem
usa um texto fixo, o detalhe usa o `resumo` da receita.

## Perguntas em aberto

Nenhuma — filtro por categoria/tag e busca ficaram explicitamente fora do
escopo (ver Não-objetivos) para não misturar esta spec com a de busca.

## Testes

- **RF-01/RNF-01 — listagem:** criar receitas publicadas e não publicadas,
  conferir que só as publicadas aparecem no contexto/response, e que o
  número de queries não cresce com o número de tags (via
  `django.test.utils.CaptureQueriesContext` ou `assertNumQueries`).
- **RF-02 — paginação:** criar mais de 9 receitas publicadas, conferir
  contagem por página e 404 em página inexistente.
- **RF-03/RF-04 — detalhe:** receita publicada retorna 200 com os campos
  no contexto; receita não publicada e slug inexistente retornam 404;
  receita sem autor renderiza sem erro.
- **RF-06 — home:** com receitas publicadas, a home contém os títulos
  esperados; sem nenhuma publicada, contém a mensagem de "em breve".
