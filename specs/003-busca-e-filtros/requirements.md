---
feature: Busca textual e filtros por categoria/tag
status: concluído
date: 2026-09-12
related:
  - 002-listagem-detalhe-receitas/requirements.md
origin: concepcao
---

# 003 — Busca textual e filtros por categoria/tag

## Contexto e problema

A spec 002 entregou a listagem e o detalhe de receitas, mas deixou de fora
de propósito qualquer forma de encontrar uma receita específica — hoje só
dá para rolar a listagem página por página. `docs/stack.md` já registra a
decisão de manter a busca simples (ORM `icontains`, sem motor de busca
dedicado); esta spec implementa exatamente isso, e aproveita para tornar
categoria e tags clicáveis (âncoras já visíveis no design, sem link).

## Objetivos

- Busca por texto (título e ingredientes) na página de listagem.
- Filtro por categoria e por tag, acessíveis tanto por link (a partir dos
  cartões/etiquetas já renderizados) quanto por URL direta.
- Combinação dos três filtros ao mesmo tempo (busca + categoria + tag).
- Paginação preservando os filtros ativos.
- Estado vazio claro quando nenhuma receita corresponde ao filtro.

## Não-objetivos

- Motor de busca dedicado (Postgres full-text search, Elasticsearch,
  `django-watson`/`django-haystack`) — fora de escopo por decisão já
  registrada em `docs/stack.md`.
- Sugestão/autocompletar termos de busca.
- Busca tolerante a erro de digitação (fuzzy matching).
- Ordenação por relevância — a listagem filtrada continua ordenada por
  data, igual à spec 002.
- Página dedicada por categoria/tag (ex.: `/receitas/categoria/<slug>/`) —
  os filtros vivem como querystring da mesma listagem (`/receitas/?...`),
  mantendo uma view só.

## Personas

- Como **leitor**, quero digitar "cenoura" e encontrar toda receita que
  tenha esse termo no título ou nos ingredientes.
- Como **leitor**, quero clicar na categoria de um cartão de receita (ex.:
  "Sobremesas") e ver só as receitas daquela categoria.
- Como **leitor**, quero clicar numa tag na página de detalhe (ex.: "sem
  glúten") e ver outras receitas com a mesma tag.

## Requisitos funcionais

### RF-01 — Busca textual

- **Given** a página de listagem tem um campo de busca
  **When** um visitante submete o termo "cenoura"
  **Then** só aparecem receitas publicadas cujo `titulo` ou `ingredientes`
  contenham "cenoura", sem diferenciar maiúsculas/minúsculas (ex.: buscar
  "cenoura" encontra "Bolo de Cenoura"). Acentuação **não** é normalizada
  (buscar "cenoura" não encontra "cenourá") — ver ADR-2 em `design.md`: a
  decisão de manter a busca em `icontains` puro (já registrada em
  `docs/stack.md`) não cobre isso, e resolver exigiria normalização extra
  ou um motor de busca dedicado, ambos fora do escopo desta spec.
- **Given** o termo buscado não corresponde a nenhuma receita
  **When** a listagem renderiza
  **Then** exibe uma mensagem indicando que nada foi encontrado para aquele
  termo (RF-05), em vez de um grid vazio sem explicação.

### RF-02 — Filtro por categoria

- **Given** um cartão de receita mostra sua categoria (ex.: "Sobremesas")
  **When** o visitante clica nela
  **Then** é levado a `/receitas/?categoria=<slug-da-categoria>`, exibindo
  só receitas publicadas daquela categoria.
- **Given** o parâmetro `categoria` não corresponde a nenhuma categoria
  existente
  **When** a listagem processa o filtro
  **Then** retorna lista vazia (RF-05), **não** um erro 500 ou 404 — filtro
  sem correspondência é um resultado válido, não uma URL inválida.

### RF-03 — Filtro por tag

- **Given** a página de detalhe mostra as tags da receita como etiquetas
  **When** o visitante clica numa etiqueta
  **Then** é levado a `/receitas/?tag=<slug-da-tag>`, exibindo só receitas
  publicadas com aquela tag.
- **Given** o parâmetro `tag` não corresponde a nenhuma tag existente
  **When** a listagem processa o filtro
  **Then** retorna lista vazia (mesmo comportamento de RF-02).

### RF-04 — Combinação de filtros

- **Given** a URL contém `?q=cenoura&categoria=sobremesas`
  **When** a listagem processa os parâmetros
  **Then** aplica os dois filtros juntos (E lógico) — só receitas de
  Sobremesas que também mencionem "cenoura".

### RF-05 — Estado vazio com contexto

- **Given** a combinação de filtros não retorna nenhuma receita
  **When** a listagem renderiza
  **Then** exibe uma mensagem amigável que menciona o termo buscado e/ou o
  filtro ativo (ex.: "Nenhuma receita encontrada para 'cenoura'."), com um
  link para limpar os filtros e voltar à listagem completa.

### RF-06 — Paginação preserva os filtros

- **Given** uma busca ou filtro retorna mais de 9 receitas
  **When** o visitante navega para a página 2
  **Then** os parâmetros de busca/filtro da URL atual (`q`, `categoria`,
  `tag`) são preservados junto com `page=2` — a paginação não reseta o
  filtro ativo.

### RF-07 — Formulário de busca acessível e consistente com os filtros

- **Given** a listagem está filtrada por categoria e/ou tag (via link)
  **When** o visitante usa o campo de busca para adicionar um termo
  **Then** o filtro de categoria/tag ativo é preservado (não é perdido ao
  submeter a busca) — o formulário mantém os filtros atuais como campos
  ocultos.
- O campo de busca tem `<label>` associado (acessibilidade), método `GET`
  (a URL resultante é compartilhável/favoritável).

## Requisitos não-funcionais

### RNF-01 — Sem N+1 adicional

A queryset filtrada reaproveita o mesmo `select_related`/
`prefetch_related` já usado por `ReceitaListView` (spec 002) — filtrar não
pode reintroduzir uma query por linha.

### RNF-02 — Filtro inválido nunca é erro 500

Parâmetro de categoria/tag que não existe, ou termo de busca vazio,
resultam em lista vazia ou listagem completa (respectivamente) — nunca uma
exceção não tratada.

## Perguntas em aberto

Nenhuma — os pontos que poderiam gerar ambiguidade (motor de busca,
página dedicada por categoria) já foram resolvidos em "Não-objetivos".

## Testes

- **RF-01:** busca por termo presente no título encontra a receita; termo
  presente só nos ingredientes também encontra; termo ausente não encontra
  nada; busca é case-insensível (não precisa cobrir acento — ver ADR-2).
- **RF-02/RF-03:** filtro por slug de categoria existente restringe
  corretamente; slug de categoria/tag inexistente retorna lista vazia sem
  erro.
- **RF-04:** busca + categoria juntos aplicam interseção, não união.
- **RF-05:** resposta contém a mensagem de "nada encontrado" e o termo
  buscado quando o resultado é vazio.
- **RF-06:** segunda página de um resultado filtrado mantém o filtro (via
  `response.context["receitas"]` e verificando a querystring dos links de
  paginação no HTML).
- **RNF-02:** `?categoria=nao-existe` e `?tag=nao-existe` retornam 200 com
  lista vazia, não 404/500.
