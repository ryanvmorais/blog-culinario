---
feature: Descoberta pelos buscadores e pelas redes sociais
status: concluído
date: 2026-11-16
related:
  - 002-listagem-detalhe-receitas/requirements.md
  - 003-busca-e-filtros/requirements.md
  - 008-correcoes-de-interface/requirements.md
  - 009-modo-demonstracao/requirements.md
origin: concepcao
---

# 010 — Descoberta pelos buscadores e pelas redes sociais

## Contexto e problema

O blog vai ganhar uma instância pública de demonstração (spec 009). O que um buscador
ou uma rede social lê dele hoje é pouco:

- **Sem endereço canônico.** Nenhuma página traz `<link rel="canonical">`. A mesma
  lista de receitas responde em `/receitas/`, `/receitas/?q=bolo`,
  `/receitas/?categoria=doces` e em qualquer combinação dos filtros (spec 003), e o
  buscador não sabe qual endereço guardar.
- **Sem Open Graph.** O `<head>` do `base.html` só tem `<title>` e `description`. Um
  link compartilhado numa rede social vira um cartão montado por adivinhação, ou
  nenhum.
- **Sem `robots.txt` e sem `sitemap.xml`.** Os dois respondem 404. O buscador só acha
  as receitas seguindo links, e não há onde dizer em que endereço está o sitemap.
- **Sem `security.txt`.** `/.well-known/security.txt` (RFC 9116) responde 404. O canal
  privado de relato existe (avisos de segurança do GitHub e o `SECURITY.md`), mas quem
  procura o contato pelo padrão não o encontra no site.

Montar endereço absoluto a partir do `Host` do pedido não serve para nada disso: o
cabeçalho vem do cliente, e um endereço canônico precisa ser um só.

## Objetivos

- Uma chave de ambiente, `URL_PUBLICA`, que é a única fonte do endereço absoluto do
  site.
- Canonical e Open Graph (sem imagem) em toda página pública.
- `robots.txt` e `sitemap.xml` servidos pela aplicação, com o sitemap listando a home,
  a lista e cada receita publicada.
- O contato de segurança em `/.well-known/security.txt` na instância de demonstração,
  com um teste que avisa antes de o `Expires` vencer.
- Para quem clona: o mesmo canonical, `robots.txt` e `sitemap.xml` no próprio deploy,
  ligados por uma variável, sem herdar o contato de segurança do repositório.

## Não-objetivos

- **Imagem de compartilhamento** (`og:image`), `twitter:card` e ícone de tela inicial.
- **Dados estruturados** (JSON-LD, `schema.org/Recipe`).
- **Versão em inglês do site** e `hreflang`: o site é em português.
- **Política de robôs de IA no código.** Se o deploy tiver um proxy com `robots.txt`
  gerenciado, o bloqueio de robôs de treino fica com ele (decisão resolvida 5).
- **Enviar o sitemap a buscadores.** É operação de quem publica, fora do código.
- **Mudar o caminho do Admin.** Fica com a spec 011 (RF-14, `ADMIN_URL`); esta spec só
  garante que o `robots.txt` não o revele (RF-04).
- **`/security.txt` na raiz** (local antigo, que a RFC 9116 aceita só como
  redirecionamento).

## Personas

- Como **quem procura uma receita**, quero que o resultado de busca e o cartão de um
  link compartilhado mostrem o título e o resumo da receita, para saber o que vou abrir.
- Como **quem clona e publica o blog**, quero canonical, `robots.txt` e `sitemap.xml`
  ligados por uma variável, para o meu deploy ser indexado com o meu endereço.
- Como **quem pesquisa segurança**, quero o contato em `/.well-known/security.txt`,
  para relatar em privado sem procurar o repositório.
- Como **aprendiz de Django**, quero ver no código como servir arquivos de descoberta
  e montar endereços absolutos sem confiar no `Host` do pedido.

## Requisitos funcionais

### Endereço público

### RF-01 — Chave `URL_PUBLICA`

- **Given** `URL_PUBLICA=https://exemplo.com.br` (com ou sem a barra final)
  **When** a aplicação sobe
  **Then** o endereço público vale `https://exemplo.com.br`, sem a barra final, e é a
  única fonte do endereço absoluto no canonical, no `og:url`, no `robots.txt`, no
  `sitemap.xml` e no `security.txt`.
- **Given** `URL_PUBLICA` com valor que não começa por `http://` ou `https://`, ou com
  caminho, query ou fragmento
  **When** a aplicação sobe
  **Then** a subida falha com `ImproperlyConfigured` que cita a chave e o formato
  esperado.
- **Given** `URL_PUBLICA` vazia ou ausente (o padrão em desenvolvimento)
  **When** a aplicação sobe
  **Then** ela sobe normalmente, e os RFs abaixo dizem o que fica de fora.

### Metadados da página

### RF-02 — Canonical e `og:url`

- **Given** `URL_PUBLICA` definida
  **When** uma página pública que estende o `base.html` é pedida
  **Then** o `<head>` traz `<link rel="canonical">` e `<meta property="og:url">` com o
  mesmo endereço: `URL_PUBLICA` + o caminho da página, sem a query string.
- **Given** `URL_PUBLICA` definida
  **When** a lista de receitas é pedida com `?page=N`, N maior que 1, com ou sem busca e
  filtros
  **Then** o canonical é `URL_PUBLICA` + `/receitas/?page=N`, e `q`, `categoria` e `tag`
  ficam de fora (a busca e os filtros não ganham endereço próprio no buscador).
- **Given** `URL_PUBLICA` vazia
  **When** qualquer página é pedida
  **Then** o `<head>` não traz canonical nem `og:url`.
- **Given** uma página de erro (403, 404, 500)
  **When** é servida
  **Then** não traz canonical nem `og:url`.

### RF-03 — Open Graph sem imagem

- **Given** uma página pública que estende o `base.html`
  **When** é servida
  **Then** o `<head>` traz `og:title` igual ao `<title>`, `og:description` igual à
  `description`, `og:site_name` "Blog Culinário" e `og:locale` `pt_BR`.
- **Given** o detalhe de uma receita
  **When** é servido
  **Then** o `og:type` é `article`; nas outras páginas, `website`.
- **Given** qualquer página
  **When** é servida
  **Then** não há `og:image` nem `twitter:card` (não-objetivos).

### Arquivos de descoberta

### RF-04 — `robots.txt`

- **Given** um pedido a `/robots.txt`
  **When** a aplicação responde
  **Then** devolve 200, `text/plain; charset=utf-8`, com `User-agent: *` e
  `Allow: /`, sem regra que impeça o rastreio das páginas públicas e sem citar o
  caminho do Admin (decisão resolvida 6).
- **Given** `URL_PUBLICA` definida
  **When** `/robots.txt` é pedido
  **Then** o arquivo termina com `Sitemap: <URL_PUBLICA>/sitemap.xml`; vazia, não há
  linha `Sitemap:`.

### RF-05 — `sitemap.xml`

- **Given** `URL_PUBLICA` definida
  **When** `/sitemap.xml` é pedido
  **Then** devolve 200, `application/xml`, um sitemap válido (protocolo sitemaps.org
  0.9) com uma `<loc>` para a home, uma para a lista de receitas e uma para cada receita
  publicada, cada `<loc>` igual ao canonical da página.
- **Given** uma receita publicada
  **When** entra no sitemap
  **Then** a entrada traz `<lastmod>` com a data do `atualizado_em` dela.
- **Given** uma receita com `publicado=False`
  **When** `/sitemap.xml` é pedido
  **Then** ela não aparece.
- **Given** `URL_PUBLICA` definida
  **When** `/sitemap.xml` é pedido
  **Then** não há páginas da lista (`?page=`), busca, filtro, login nem cadastro.
- **Given** `URL_PUBLICA` vazia
  **When** `/sitemap.xml` é pedido
  **Then** devolve 404: sem endereço configurado, o sitemap não é montado a partir do
  `Host`.

### RF-06 — `security.txt` na demonstração

- **Given** `MODO_DEMONSTRACAO=True`
  **When** `/.well-known/security.txt` é pedido
  **Then** devolve 200, `text/plain; charset=utf-8`, com `Contact:` apontando para a
  criação de aviso de segurança no repositório
  (`<URL_REPOSITORIO>/security/advisories/new`), um único `Expires:` em ISO 8601,
  `Preferred-Languages: pt, en` e `Policy:` apontando para o `SECURITY.md` do
  repositório.
- **Given** `MODO_DEMONSTRACAO=True` e `URL_PUBLICA` definida
  **When** `/.well-known/security.txt` é pedido
  **Then** o arquivo traz `Canonical: <URL_PUBLICA>/.well-known/security.txt`; com
  `URL_PUBLICA` vazia, não há linha `Canonical:`.
- **Given** `MODO_DEMONSTRACAO=False`
  **When** `/.well-known/security.txt` é pedido
  **Then** devolve 404: quem publica o próprio blog não herda o contato do repositório
  do projeto.

### Sem regressão

### RF-07 — Sem `URL_PUBLICA`, as páginas seguem iguais fora do Open Graph

- **Given** `URL_PUBLICA` vazia
  **When** qualquer página é pedida
  **Then** título, `description` e o restante do `<head>` são os de hoje, e a única
  diferença são as tags `og:*` sem endereço do RF-03.

## Requisitos não-funcionais

### RNF-01 — Sem dependência nova de runtime

O `pyproject.toml` não ganha dependência de runtime, e o `INSTALLED_APPS` só ganha app
se for do próprio Django.

### RNF-02 — Postura de segurança mantida

Nenhum template ganha `<script>` ou estilo inline, e
`DEBUG=False uv run python manage.py check --deploy` segue sem aviso novo.

### RNF-03 — Endereço nunca vindo do pedido

Canonical, `og:url`, `sitemap.xml`, a linha `Sitemap:` e o `Canonical:` do
`security.txt` saem só de `URL_PUBLICA`; nenhum deles é montado a partir do `Host` ou
do `X-Forwarded-*` do pedido.

### RNF-04 — Lighthouse CI segue verde

As 5 páginas auditadas seguem com SEO, acessibilidade e boas práticas ≥ 95 nos dois
perfis, com o `robots.txt` agora servido e válido para o Lighthouse.

### RNF-05 — Documentado para quem clona

`URL_PUBLICA` entra no `.env.example` com o formato e o efeito, e no `README.md` e no
`README.en.md` (mesma seção, nos dois idiomas). A mudança de sentido do
`MODO_DEMONSTRACAO` (além do formulário, o `security.txt`) entra nos mesmos lugares.

## Decisões resolvidas

1. **Endereço público numa chave própria, `URL_PUBLICA`** (2026-11-16). Derivar do
   primeiro item do `ALLOWED_HOSTS` foi descartado: a ordem da lista passaria a ter um
   sentido implícito, frágil com `www` ou um segundo domínio. Usar o `Host` do pedido
   foi descartado pelo RNF-03.
2. **Open Graph sem imagem** (2026-11-16): título, descrição, tipo e nome do site saem
   dos blocos que as páginas já preenchem. Sem `og:image` o cartão fica menor, mas não
   há imagem própria de divulgação para cada página, e a capa da receita é conteúdo do
   banco, não do repositório.
3. **A busca e os filtros não ganham canonical próprio** (2026-11-16): são recortes da
   mesma lista, e indexar cada combinação de `q`, `categoria` e `tag` multiplicaria
   páginas quase iguais. A paginação fica no canonical, porque a página 2 tem receitas
   que a 1 não tem.
4. **`security.txt` só com o modo demonstração** (2026-11-16). O contato é o do
   repositório do projeto; num deploy que não é a demo, ele apontaria para quem não
   responde por aquele site. O `Expires` fica fixo no repositório, e um teste falha 30
   dias antes do vencimento.
5. **O `robots.txt` da aplicação convive com o de um proxy.** Um proxy com `robots.txt`
   gerenciado (como o da Cloudflare) põe o bloco dele antes do conteúdo da origem, que
   segue valendo. Sem proxy na frente, vale só o da aplicação.
6. **`robots.txt` sem o Admin** (2026-11-16, revista no mesmo dia): a primeira versão
   tinha `Disallow: /admin/`, porque o caminho era o padrão do Django e não era segredo.
   Com o `ADMIN_URL` da spec 011 (RF-14), um `Disallow` entregaria o caminho trocado;
   o arquivo passa a ser `User-agent: *` / `Allow: /`, e a tela de
   login do Admin já traz `<meta name="robots" content="NONE,NOARCHIVE">`. As páginas
   de login e cadastro seguem rastreáveis, porque o Lighthouse CI as audita.

## Testes

### RF-08 — Suíte da descoberta

A suíte (`uv run pytest`, sem rede) cobre, com `override_settings` quando preciso:

- `URL_PUBLICA`: normalização da barra final, falha de subida com valor inválido e
  subida normal com ela vazia (RF-01);
- canonical e `og:url` com e sem `URL_PUBLICA`, sem a query string, com `?page=N` e sem
  `q`/`categoria`/`tag` na lista, e ausentes nas páginas de erro (RF-02);
- `og:title`, `og:description`, `og:site_name`, `og:locale` e o `og:type` de cada tipo
  de página, sem `og:image` (RF-03);
- `robots.txt` com e sem `URL_PUBLICA` (RF-04);
- `sitemap.xml` válido, com home, lista e só as receitas publicadas, `lastmod` igual ao
  `atualizado_em`, cada `<loc>` igual ao canonical, e 404 sem `URL_PUBLICA` (RF-05);
- `security.txt` só com o modo, os campos obrigatórios, `Contact:` em `https://`, um
  único `Expires`, e falha quando o `Expires` está a menos de 30 dias ou a mais de 366
  dias da data do teste (RF-06);
- o mesmo endereço absoluto em todos os pontos, nunca vindo do `Host` (RNF-03);
- o `<head>` sem `URL_PUBLICA` igual ao de hoje fora do Open Graph (RF-07).
