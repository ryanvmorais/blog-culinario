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

# 010 — Descoberta pelos buscadores e pelas redes sociais — design

## Visão geral da abordagem

`URL_PUBLICA` é lida e validada no `settings/base.py` por uma função de um módulo
pequeno, `blog_culinario/endereco.py`, que também monta qualquer endereço absoluto a
partir dela (`url_absoluta`). Tudo o que precisa de endereço absoluto passa por essa
função, e nada lê o `Host` do pedido (RNF-03).

O `<head>` do `base.html` ganha o canonical, o `og:url` e as tags `og:*`. O canonical
vem de um context processor (`contexto_descoberta`), que junta `URL_PUBLICA`, o caminho
do pedido e, só na lista de receitas, o `page`. O título e a descrição de cada página
continuam nos blocos que os templates filhos já preenchem; uma tag de template,
`{% capturar %}`, guarda o que o bloco renderizou numa variável, para o mesmo texto ir
ao `<title>` e ao `og:title` sem duplicar nada nos filhos.

Os três arquivos de descoberta são views de `blog_culinario/descoberta.py`: o
`robots.txt` e o `security.txt` são texto montado em Python; o `sitemap.xml` usa o
`django.contrib.sitemaps`, com o domínio e o protocolo tirados de `URL_PUBLICA` em vez
do pedido.

## Layout de módulos

| Arquivo | Muda | O quê |
|---|---|---|
| `blog_culinario/endereco.py` | novo | `normalizar_url_publica` e `url_absoluta` (RF-01, RNF-03) |
| `blog_culinario/descoberta.py` | novo | context processor, `SitemapPublico`, `PaginasSitemap` e as views `robots_txt`, `sitemap` e `security_txt` (RF-02, RF-04 a RF-06) |
| `receitas/sitemaps.py` | novo | `ReceitaSitemap` (RF-05) |
| `nucleo/templatetags/__init__.py` | novo | pacote de tags |
| `nucleo/templatetags/metadados.py` | novo | tag `{% capturar %}` (RF-03, ADR-2) |
| `blog_culinario/settings/base.py` | muda | `URL_PUBLICA`, `django.contrib.sitemaps` no `INSTALLED_APPS`, o context processor |
| `blog_culinario/urls.py` | muda | `/robots.txt`, `/sitemap.xml`, `/.well-known/security.txt` |
| `templates/base.html` | muda | canonical, `og:url` e `og:*` no `<head>` |
| `templates/403.html`, `templates/404.html` | muda | esvaziam o bloco do endereço canônico (RF-02) |
| `receitas/templates/receitas/detalhe.html` | muda | `og:type` `article` (RF-03) |
| `nucleo/test_descoberta.py` | novo | a suíte do RF-08 |
| `.github/workflows/lighthouse.yml` | muda | `URL_PUBLICA` no servidor auditado (RNF-04) |
| `.env.example`, `README.md`, `README.en.md`, `CLAUDE.md` | muda | documentação (RNF-05) |

## Modelo de dados

Nenhuma mudança. O sitemap lê `Receita.slug`, `Receita.publicado` e
`Receita.atualizado_em`, que já existem (spec 001).

## Componentes

### `blog_culinario/endereco.py`

- `normalizar_url_publica(valor: str) -> str`: devolve `""` para valor vazio ou só com
  espaços. Senão, separa com `urllib.parse.urlsplit` e exige esquema `http` ou `https`,
  host presente, sem usuário nem senha, caminho vazio ou `/`, sem query e sem fragmento.
  Devolve `esquema://host[:porta]`, sem a barra final. Fora disso, levanta
  `ImproperlyConfigured("URL_PUBLICA deve ser só esquema e host, como https://exemplo.com.br; recebido: …")`.
- `url_absoluta(caminho: str) -> str`: `settings.URL_PUBLICA + caminho`, ou `""` quando
  `URL_PUBLICA` está vazia. O caminho já vem começando por `/` (saída de `reverse` ou de
  `request.path`).

O módulo só importa `urllib.parse`, `django.conf.settings` e
`django.core.exceptions`, porque o `settings/base.py` o importa durante a carga das
configurações (ADR-5).

### `blog_culinario/settings/base.py`

```python
URL_PUBLICA = normalizar_url_publica(env.str("URL_PUBLICA", default=""))
```

Numa seção própria, "Descoberta (spec 010)", depois do modo demonstração. O
`INSTALLED_APPS` ganha `django.contrib.sitemaps` (o template `sitemap.xml` vem dele) e a
lista de context processors ganha `blog_culinario.descoberta.contexto_descoberta`.

### `blog_culinario/descoberta.py`

**Context processor** `contexto_descoberta(request) -> dict[str, str]`: devolve
`url_canonica`, vazia quando `URL_PUBLICA` está vazia. Senão,
`url_absoluta(escape_uri_path(request.path))`, e, quando o pedido resolveu para
`receitas:lista` e o `page` da query é um inteiro maior que 1, acrescenta
`?page=N`. Nenhum outro parâmetro entra (decisão resolvida 3).

**Sitemaps:**

- `SitemapPublico(Sitemap)`: sobrescreve `get_protocol` e `get_domain` para devolver o
  esquema e o host de `URL_PUBLICA`, ignorando o `RequestSite` que a view do Django
  monta a partir do pedido (ADR-1).
- `PaginasSitemap(SitemapPublico)`: `items()` devolve `["nucleo:home",
  "receitas:lista"]`, e `location(item)` é `reverse(item)`. Sem `lastmod`.

**Views** (funções, `require_GET`):

- `robots_txt(request)`: linhas `User-agent: *`, `Disallow: /admin/` e, com
  `URL_PUBLICA`, uma linha em branco e `Sitemap: <url_absoluta("/sitemap.xml")>`.
  `HttpResponse(..., content_type="text/plain; charset=utf-8")`.
- `sitemap(request, sitemaps)`: `Http404` sem `URL_PUBLICA`; senão, delega para
  `django.contrib.sitemaps.views.sitemap(request, sitemaps=sitemaps)`, que já devolve
  `application/xml`, o `X-Robots-Tag: noindex` e o `Last-Modified` da receita mais
  recente.
- `security_txt(request)`: `Http404` sem o modo demonstração
  (`modo_demonstracao_ligado()`, spec 009). Senão, as linhas:
  ```
  Contact: <URL_REPOSITORIO>/security/advisories/new
  Expires: <EXPIRACAO_SECURITY_TXT>
  Preferred-Languages: pt, en
  Policy: <URL_REPOSITORIO>/blob/main/SECURITY.md
  Canonical: <url_absoluta("/.well-known/security.txt")>   (só com URL_PUBLICA)
  ```
  `URL_REPOSITORIO` vem de `blog_culinario/demonstracao.py`. `EXPIRACAO_SECURITY_TXT`
  é uma constante do módulo, `"2027-11-01T00:00:00Z"` (ADR-6).

### `receitas/sitemaps.py`

`ReceitaSitemap(SitemapPublico)`: `items()` devolve
`Receita.objects.filter(publicado=True)` (a ordem vem do `Meta.ordering`, então o
paginador do sitemap não avisa de lista sem ordem); `location(receita)` é
`reverse("receitas:detalhe", kwargs={"slug": receita.slug})`; `lastmod(receita)` é
`receita.atualizado_em`, que o template do Django escreve como `AAAA-MM-DD`.

### `nucleo/templatetags/metadados.py`

`{% capturar nome %}…{% endcapturar %}` renderiza o conteúdo, tira os espaços das
pontas, guarda o resultado no contexto como `SafeString` (o conteúdo já saiu escapado
pelo autoescape) e não escreve nada no lugar. O nó declara
`child_nodelists = ("nodelist",)`, para o `{% extends %}` achar os `{% block %}` de
dentro e os filhos continuarem sobrescrevendo `titulo` e `descricao` como hoje (ADR-2).

### `templates/base.html`

```django
{% load static metadados %}
…
{% capturar titulo_pagina %}{% block titulo %}Blog Culinário{% endblock %}{% endcapturar %}
{% capturar descricao_pagina %}{% block descricao %}Receitas simples…{% endblock %}{% endcapturar %}
<title>{{ titulo_pagina }}</title>
<meta name="description" content="{{ descricao_pagina }}" />
{% block endereco_canonico %}
  {% if url_canonica %}
    <link rel="canonical" href="{{ url_canonica }}" />
    <meta property="og:url" content="{{ url_canonica }}" />
  {% endif %}
{% endblock %}
<meta property="og:type" content="{% block og_tipo %}website{% endblock %}" />
<meta property="og:title" content="{{ titulo_pagina }}" />
<meta property="og:description" content="{{ descricao_pagina }}" />
<meta property="og:site_name" content="Blog Culinário" />
<meta property="og:locale" content="pt_BR" />
```

Os textos padrão de `titulo` e `descricao` ficam os de hoje (RF-07). O `403.html` e o
`404.html` declaram `{% block endereco_canonico %}{% endblock %}`; o `500.html` não
estende o `base.html` (spec 008) e segue sem nada disso. O `detalhe.html` declara
`{% block og_tipo %}article{% endblock %}`.

### `.github/workflows/lighthouse.yml`

O passo que sobe o servidor ganha `URL_PUBLICA: "http://127.0.0.1:8000"`. Assim o
canonical das páginas auditadas aponta para o mesmo host que o Lighthouse abriu (a
auditoria de canonical reprova endereço de outro domínio), e o `robots.txt` auditado
traz a linha `Sitemap:`.

### Documentação

- `.env.example`: `URL_PUBLICA=` com o formato, o efeito (canonical, `og:url`,
  `sitemap.xml`, `Sitemap:` do `robots.txt`) e que vazia desliga tudo isso; o
  comentário do `MODO_DEMONSTRACAO` passa a citar o `security.txt`.
- `README.md` e `README.en.md`: a frase do modo demonstração cita o `security.txt`, e
  uma frase nova, nos dois idiomas e na mesma seção, apresenta `URL_PUBLICA` (RNF-05).
- `CLAUDE.md`: `endereco.py` e `descoberta.py` na árvore de arquitetura.

## Interfaces

| Método e caminho | Nome da rota | Resposta |
|---|---|---|
| `GET /robots.txt` | `robots_txt` | 200, `text/plain; charset=utf-8` |
| `GET /sitemap.xml` | `sitemap` | 200, `application/xml`; 404 sem `URL_PUBLICA` |
| `GET /.well-known/security.txt` | `security_txt` | 200, `text/plain; charset=utf-8`; 404 sem o modo |

As três rotas ficam no `blog_culinario/urls.py`, sem namespace, porque são caminhos
fixos da raiz do site. O `sitemap` recebe
`{"sitemaps": {"paginas": PaginasSitemap, "receitas": ReceitaSitemap}}` como kwargs da
rota, o padrão da documentação do Django; montar o dicionário no `urls.py` evita que
`descoberta.py` importe de `receitas`. Outro método HTTP responde 405.

Variável de ambiente nova: `URL_PUBLICA` (opcional; vazia por padrão).

## ADRs

### ADR-1 — `django.contrib.sitemaps` com domínio e protocolo de `URL_PUBLICA`

**Decisão.** O sitemap usa o framework de sitemaps do Django, com uma classe base que
sobrescreve `get_domain` e `get_protocol`.

**Alternativas.** (a) Template XML próprio e uma view que monta a lista. (b) O framework
com o `django.contrib.sites` e um `Site` cadastrado no banco.

**Porquê.** O framework já escapa o XML, pagina acima de 50 mil endereços, escreve o
`lastmod` e manda o `Last-Modified` e o `X-Robots-Tag`; o projeto é educacional, e é
assim que a documentação do Django ensina. A view do framework monta o domínio a partir
do pedido (`RequestSite`), e sobrescrever os dois métodos é o ponto de extensão
documentado para trocar isso. O `sites` (b) põe o endereço no banco, numa segunda fonte
além da variável de ambiente, e exige migration.

**Trade-off.** O `django.contrib.sitemaps` entra no `INSTALLED_APPS` (permitido pelo
RNF-01), e quem lê o código precisa saber que o `RequestSite` que a view passa é
ignorado.

### ADR-2 — Tag `{% capturar %}` para o título e a descrição irem a dois lugares

**Decisão.** O `base.html` captura o que os blocos `titulo` e `descricao` renderizaram e
usa as variáveis no `<title>`, na `description` e nas tags `og:*`.

**Alternativas.** (a) Blocos `og_titulo` e `og_descricao` preenchidos em cada um dos sete
templates filhos. (b) Título e descrição no contexto de cada view. (c) Um pacote de
terceiros com a mesma tag.

**Porquê.** A linguagem de templates do Django não renderiza o mesmo bloco duas vezes.
Com a tag, os filhos não mudam e não há texto duplicado que possa divergir; (a) duplica
linhas em cada filho, (b) espalha texto de página pelas views e (c) quebra o RNF-01. A tag tem
poucas linhas e mostra um ponto pouco visto do Django: tag de bloco própria que convive
com a herança de templates.

**Trade-off.** Uma tag própria para manter, e quem lê o `base.html` precisa abrir o
`metadados.py` para entender o `{% capturar %}`.

### ADR-3 — Canonical por context processor, com as páginas de erro esvaziando o bloco

**Decisão.** `contexto_descoberta` calcula `url_canonica` para todo pedido; o `403.html`
e o `404.html` sobrescrevem `endereco_canonico` com um bloco vazio.

**Alternativas.** (a) Cada template filho declara o próprio canonical. (b) Um middleware
que acrescenta o cabeçalho `Link: <…>; rel="canonical"`.

**Porquê.** O canonical é o caminho do pedido em quase todas as páginas, e a única
exceção (o `page` da lista) cabe numa condição. Página nova que estende o `base.html`
ganha o canonical sem lembrar de nada. O 404 de uma receita não publicada é servido no
caminho da receita, e por isso o bloco precisa ser esvaziado no template, não decidido
pela rota. O cabeçalho (b) não é visto pelo `og:url` nem por quem lê o HTML.

**Trade-off.** Ler o `page` da query no context processor duplica um pouco do que o
`ListView` faz. `?page=last`, que o `ListView` aceita, cai no canonical da página 1; a
paginação do template só gera links numéricos.

### ADR-4 — `robots.txt` e `security.txt` montados em Python

**Decisão.** As duas views juntam uma lista de linhas e devolvem `HttpResponse`.

**Alternativas.** Templates de texto em `templates/`, renderizados com
`content_type="text/plain"`.

**Porquê.** São poucas linhas, com uma ou duas condicionais, e o template de texto
espalha linhas em branco a cada `{% if %}`. Em Python, o teste compara a lista de linhas
e o formato fica sob controle.

**Trade-off.** Mudar o texto pede editar Python, não um arquivo de template.

### ADR-5 — Validação de `URL_PUBLICA` num módulo sem dependências do Django web

**Decisão.** `normalizar_url_publica` mora em `blog_culinario/endereco.py`, que o
`settings/base.py` importa, e a subida falha com `ImproperlyConfigured`.

**Alternativas.** (a) A função dentro do próprio `settings/base.py`. (b) Validar no
primeiro uso, por um system check.

**Porquê.** O arquivo de settings não é lugar de lógica testável, e importar
`descoberta.py` (views, sitemaps) durante a carga das configurações arrisca import
circular. Falhar na subida pega o erro no deploy, não no primeiro buscador; é o mesmo
comportamento do `DJANGO_SECRET_KEY` ausente em produção.

**Trade-off.** Mais um módulo pequeno em `blog_culinario/`.

### ADR-6 — `Expires` fixo no código, vigiado por teste

**Decisão.** `EXPIRACAO_SECURITY_TXT` é uma constante; um teste falha quando ela está a
menos de 30 dias ou a mais de 366 dias da data em que o teste roda.

**Alternativas.** (a) `Expires` calculado na hora (hoje + 1 ano). (b) Variável de
ambiente.

**Porquê.** A RFC 9116 usa o `Expires` para o leitor saber se o contato ainda é
cuidado; uma data que se renova sozinha diz que sim mesmo com o projeto abandonado. O
teste vermelho no CI é o lembrete de revisar o contato e mover a data.

**Trade-off.** Uma vez por ano, um PR só para mover a data, e o CI de qualquer PR fica
vermelho a partir de 30 dias antes do vencimento.

## Impacto no código existente

- **`base.html`:** o `<title>` e a `description` passam a sair das variáveis capturadas;
  o texto renderizado não muda (RF-07). As tags `og:*` entram em todas as páginas que
  estendem o `base.html`.
- **Testes existentes** que comparam o `<head>` (`nucleo/test_interface.py`,
  `nucleo/test_comentarios_templates.py`) seguem valendo; a tag nova usa comentário
  `{# #}` de uma linha, como a regra pede.
- **Sem migration.** O `django.contrib.sitemaps` não tem modelos.
- **Lighthouse CI:** o `robots.txt`, antes 404, passa a ser auditado (RNF-04), e as
  páginas ganham canonical para o host do próprio runner.
- **Produção:** nada muda sem `URL_PUBLICA` e sem o modo; a spec de hospedagem define o
  valor no deploy.

## Estratégia de testes

Testes de integração com o `Client` do Django, em `nucleo/test_descoberta.py`, com
`override_settings(URL_PUBLICA=…, MODO_DEMONSTRACAO=…)`; sem rede e sem mock.

- **`endereco.py`:** testes de unidade de `normalizar_url_publica`, parametrizados com
  os casos válidos (barra final, porta) e os inválidos (sem esquema, `ftp://`, caminho,
  query, fragmento, usuário) (RF-01).
- **Canonical e Open Graph:** pedido a cada página pública com `HTTP_HOST` diferente do
  host de `URL_PUBLICA`, conferindo que o canonical e o `og:url` vêm só de `URL_PUBLICA`
  (RNF-03); lista com `?page=2&q=bolo&categoria=x`; receita não publicada (404) e 403
  sem canonical (RF-02); `og:title` igual ao `<title>` e `og:description` igual à
  `description` em cada página, `og:type` por tipo (RF-03).
- **Sem `URL_PUBLICA`:** o `<head>` da home, com as tags `og:*` removidas, igual ao de
  antes, comparado por um trecho fixo (RF-07).
- **`robots.txt`, `sitemap.xml` e `security.txt`:** status, `Content-Type` e conteúdo; o
  sitemap lido com `xml.etree.ElementTree`, com receitas publicadas e não publicadas
  criadas no teste, conferindo os `<loc>` contra o canonical de cada página e o
  `<lastmod>` contra o `atualizado_em` (RF-04 a RF-06).
- **`Expires`:** a constante lida como data e comparada com `timezone.now()` (ADR-6).

## Desvios

1. **`require_safe` no lugar de `require_GET`** (RF-04, RF-05, RF-06; Componentes,
   "Views"). O `require_GET` recusa `HEAD` com 405, e há robôs que conferem o arquivo
   com `HEAD` antes do `GET`. O `require_safe` aceita os dois; os outros métodos
   seguem respondendo 405, como a seção "Interfaces" pede.

## Notas de implementação

- **Testes:** 202 → 256 (54 novos, todos em `nucleo/test_descoberta.py`): 22 da
  `URL_PUBLICA`, 17 do canonical e do Open Graph, 15 dos arquivos de descoberta.
- **`<head>` sem `URL_PUBLICA` (RF-07):** renderizado antes e depois da mudança na
  home, na lista, num detalhe, no login, no cadastro e no 404, e comparado sem as
  linhas `og:*`: igual. A única diferença de texto é a `<meta name="description">`,
  que passou de várias linhas para uma, com os mesmos atributos.
- **`check --deploy`** com `DEBUG=False`: os mesmos três avisos da `main`
  (`mail.E001` do backend de e-mail de console, `security.W009` da chave usada no
  teste e `security.W021`), nenhum novo (RNF-02). `URL_PUBLICA` com caminho derruba
  a subida com `ImproperlyConfigured`.
- **No `runserver`**, com `URL_PUBLICA` e o modo ligados: `robots.txt`,
  `security.txt` e `sitemap.xml` (home, lista e as seis receitas publicadas, com
  `lastmod`) conferidos, e `HEAD /robots.txt` responde 200.
- **`mypy` e o `Sitemap`:** nos stubs o `Sitemap` é genérico, mas em runtime
  `Sitemap[Any]` levanta `TypeError`; a classe base leva um
  `# type: ignore[type-arg]` com o motivo, e a assinatura da view usa o tipo genérico
  só na anotação.

