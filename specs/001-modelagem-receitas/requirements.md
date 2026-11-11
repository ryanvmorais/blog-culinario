---
feature: Modelagem de domínio das receitas (Categoria, Receita, Tag)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 001 — Modelagem de domínio das receitas

## Contexto e problema

O app `receitas` existe só como esqueleto (`startapp`, sem models). Toda
funcionalidade seguinte do projeto — listagem, página de detalhe, busca,
admin de conteúdo — depende de um domínio modelado corretamente primeiro.
Esta spec cobre só a **modelagem** (models + admin básico), não as views
públicas nem templates de listagem/detalhe (specs seguintes).

## Objetivos

- Modelar `Categoria`, `Tag` e `Receita` com os relacionamentos corretos.
- Gerar slugs automaticamente para URLs amigáveis (`/receitas/bolo-de-cenoura/`).
- Registrar os três models no Django admin de forma administrável (busca,
  filtro, preview de imagem).
- Validar upload de imagem de capa (tipo e tamanho) na camada de modelo.

## Não-objetivos

- Views/templates públicos de listagem e detalhe de receita (spec seguinte).
- Busca por texto (spec seguinte).
- Comentários (spec futura, depende de `usuarios`).
- Cadastro/perfil de usuário customizado — o autor da receita usa o `User`
  padrão do `django.contrib.auth` (spec de `usuarios` trata login/registro).

## Personas

- Como **administrador do blog**, quero cadastrar uma receita completa pelo
  Django admin (título, ingredientes, modo de preparo, categoria, tags,
  imagem), para publicar conteúdo sem precisar de uma tela customizada ainda.
- Como **leitor** (nas specs seguintes, que consomem este modelo), quero que
  cada receita tenha categoria e tags para eu conseguir navegar por assunto.

## Requisitos funcionais

### RF-01 — Modelo Categoria

- **Given** o admin acessa "Adicionar Categoria"
  **When** preenche apenas o campo `nome` (ex.: "Sobremesas") e salva
  **Then** a categoria é criada com um `slug` gerado automaticamente a partir
  do nome (ex.: `sobremesas`), único no banco.
- **Given** já existe uma categoria com slug `sobremesas`
  **When** outra categoria é criada com o mesmo `nome`
  **Then** o slug recebe um sufixo que garante unicidade (ex.: `sobremesas-2`).

### RF-02 — Modelo Tag

- **Given** o admin acessa "Adicionar Tag"
  **When** preenche o campo `nome` (ex.: "sem glúten") e salva
  **Then** a tag é criada com `slug` único gerado automaticamente, seguindo a
  mesma regra de unicidade de RF-01.

### RF-03 — Modelo Receita — campos e relacionamentos

- **Given** o admin acessa "Adicionar Receita"
  **When** preenche título, resumo, ingredientes, modo de preparo, tempo de
  preparo (minutos), porções, categoria e ao menos uma tag, e salva
  **Then** a receita é criada com `slug` único gerado a partir do título,
  `autor` preenchido com o usuário autenticado, `criado_em`/`atualizado_em`
  preenchidos automaticamente, e `publicado=False` por padrão (rascunho).
- **Given** uma receita existente
  **When** o admin marca `publicado=True` e salva
  **Then** a receita passa a estar apta a aparecer nas views públicas (a
  view em si é escopo da próxima spec — este requisito garante só que o
  campo existe e persiste corretamente).
- **Given** uma `Categoria` é excluída
  **When** existem receitas associadas a ela
  **Then** a exclusão é bloqueada pelo Django (`on_delete=PROTECT`) — não é
  permitido apagar uma categoria em uso, para não deixar receita órfã.
- **Given** uma `Tag` é excluída
  **When** existem receitas associadas a ela
  **Then** a receita permanece intacta, só perde a associação com aquela tag
  (`ManyToManyField`, sem necessidade de `PROTECT`).
- **Given** o usuário (autor) de uma receita é excluído da base
  **When** a exclusão do usuário é confirmada
  **Then** a receita permanece no banco com `autor=NULL`
  (`on_delete=SET_NULL`, `null=True`), preservando o conteúdo.

### RF-04 — Upload e validação de imagem de capa

- **Given** o admin envia um arquivo de imagem de capa ao salvar uma receita
  **When** o arquivo é maior que 5 MB ou não é um formato de imagem válido
  (JPEG/PNG/WebP)
  **Then** o formulário do admin rejeita o salvamento e exibe uma mensagem de
  erro clara, sem gravar o arquivo em `media/`.
- **Given** uma receita sem imagem de capa definida
  **When** ela é salva
  **Then** o campo aceita ficar vazio (`blank=True`) — imagem não é
  obrigatória para criar uma receita.

### RF-05 — Admin utilizável

- **Given** o admin acessa a listagem de receitas em `/admin/`
  **When** a página carrega
  **Then** exibe título, categoria, autor, `publicado` e `criado_em` como
  colunas, com filtro por categoria/publicado e busca por título.
- **Given** o admin acessa a listagem de categorias ou tags em `/admin/`
  **When** a página carrega
  **Then** exibe nome e slug, com o slug preenchido automaticamente no
  formulário conforme o nome é digitado (`prepopulated_fields`).

## Requisitos não-funcionais

### RNF-01 — Integridade referencial

Todas as chaves estrangeiras e M2M devem ter `on_delete`/comportamento
explícito (nunca o padrão implícito do Django) — ver RF-03 para a política de
cada relacionamento.

### RNF-02 — Sem N+1 óbvio no admin

O `ModelAdmin` de `Receita` deve declarar `list_select_related`/
`autocomplete_fields` para categoria e autor, evitando que a listagem do
admin dispare uma query por linha à medida que o volume de receitas cresce.

### RNF-03 — Migrations limpas

Uma única migration inicial por app (`0001_initial`), sem migrations
intermediárias de ajuste — o modelo deve nascer correto, não ser corrigido em
cima depois dentro desta mesma spec.

## Perguntas em aberto

Nenhuma — as decisões de relacionamento (RF-03) já foram resolvidas acima com
a política de `on_delete` explícita por caso.

## Testes

- **RF-01/RF-02 — geração e unicidade de slug:** criar duas categorias/tags
  com o mesmo nome e conferir que os slugs não colidem.
- **RF-03 — relacionamentos e defaults:** criar uma receita mínima e conferir
  `publicado=False`, timestamps preenchidos; excluir categoria em uso e
  conferir que levanta `ProtectedError`; excluir autor e conferir
  `autor is None` na receita remanescente.
- **RF-04 — validação de imagem:** tentar salvar com arquivo > 5 MB e com
  extensão inválida, conferir que ambos levantam `ValidationError`.
- **RF-05 — admin:** smoke test de que `/admin/receitas/receita/` e as
  listagens de categoria/tag respondem 200 para um usuário staff.
