---
feature: Busca textual e filtros por categoria/tag
status: concluído
date: 2026-09-12
related:
  - 002-listagem-detalhe-receitas/requirements.md
origin: concepcao
---

# 003 — Busca textual e filtros por categoria/tag — design

## Visão geral da abordagem

Toda a lógica entra em `ReceitaListView.get_queryset()` (spec 002), lendo
`q`, `categoria` e `tag` de `request.GET` e aplicando cada filtro só quando
presente. Um `get_context_data()` novo expõe os valores atuais dos
filtros (para preencher o formulário) e uma querystring sem `page` (para a
paginação não perder o filtro). Categoria e tags, já renderizadas nos
templates da spec 002, viram links para essa mesma URL com o parâmetro
correspondente — nenhuma view nova.

## Layout de módulos

```
receitas/
  views.py    # ReceitaListView ganha get_queryset() com filtros + get_context_data()
  templates/receitas/
    lista.html  # + formulário de busca, mensagem de estado vazio com contexto
templates/includes/
  cartao_receita.html  # categoria vira <a> para ?categoria=<slug>
  paginacao.html        # links carregam a querystring de filtro
receitas/templates/receitas/detalhe.html  # etiquetas de tag viram <a> para ?tag=<slug>
static/css/base.css  # + .formulario-busca; .etiqueta ganha text-decoration: none
```

## Componentes

### `ReceitaListView.get_queryset()` (RF-01 a RF-04, RNF-01, RNF-02)

```python
def get_queryset(self) -> QuerySet[Receita]:
    queryset = (
        Receita.objects.filter(publicado=True)
        .select_related("categoria", "autor")
        .prefetch_related("tags")
    )
    termo = self.request.GET.get("q", "").strip()
    if termo:
        queryset = queryset.filter(
            Q(titulo__icontains=termo) | Q(ingredientes__icontains=termo)
        )
    categoria_slug = self.request.GET.get("categoria", "").strip()
    if categoria_slug:
        queryset = queryset.filter(categoria__slug=categoria_slug)
    tag_slug = self.request.GET.get("tag", "").strip()
    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)
    return queryset
```

Cada filtro é independente e opcional — combiná-los é só encadear
`.filter()` (RF-04, AND por construção). Slug inexistente simplesmente não
bate com nenhuma linha (RF-02/RF-03/RNF-02): sem exceção, resultado vazio.

### `ReceitaListView.get_context_data()` (RF-06, RF-07)

Acrescenta ao contexto: `termo_busca`, `categoria_selecionada`,
`tag_selecionada` (ecoam os parâmetros atuais, para o formulário e para os
hidden inputs) e `querystring` (`request.GET` copiado, sem a chave `page`,
já `urlencode()`-ado) — usado pela paginação para não perder o filtro.

### Formulário de busca (`lista.html`, RF-01, RF-07)

`<form method="get">` com `<label for>` + `<input type="search" name="q">`
e, condicionalmente, `<input type="hidden" name="categoria">`/`name="tag"`
quando `categoria_selecionada`/`tag_selecionada` estiverem ativos — assim,
buscar um termo enquanto uma categoria está filtrada não descarta a
categoria.

### Estado vazio com contexto (RF-05)

Quando `receitas` (o `object_list` paginado) vem vazio, o template mostra
uma mensagem citando `termo_busca` quando presente, e um link para
`{% url 'receitas:lista' %}` (sem parâmetros) para "ver todas as
receitas".

### Categoria/tag clicáveis (RF-02, RF-03)

- `templates/includes/cartao_receita.html`: a `<span
  class="cartao-receita__categoria">` vira `<a class="cartao-receita__categoria"
  href="{% url 'receitas:lista' %}?categoria={{ receita.categoria.slug }}">`.
- `receitas/templates/receitas/detalhe.html`: cada `<li class="etiqueta">`
  vira `<a class="etiqueta" href="{% url 'receitas:lista' %}?tag={{ tag.slug }}">`.

### Paginação com filtro (`paginacao.html`, RF-06)

Os links "anterior"/"próxima" passam a apender `&{{ querystring }}` (do
contexto acima) quando não vazio, além de `?page=N`.

## Modelo de dados

Nenhuma mudança — filtros usam campos e relacionamentos já existentes
(`Receita.titulo`, `.ingredientes`, `.categoria.slug`, `.tags.slug`).

## Interfaces

| Parâmetro GET | Efeito |
|---|---|
| `q` | Filtra por `titulo`/`ingredientes` (`icontains`, RF-01) |
| `categoria` | Filtra por `categoria__slug` (RF-02) |
| `tag` | Filtra por `tags__slug` (RF-03) |
| `page` | Paginação já existente (spec 002), combinável com os acima |

Todos opcionais e combináveis na mesma rota `GET /receitas/` — nenhuma URL
nova.

## ADRs

### ADR-1 — Filtros via querystring na mesma `ReceitaListView`

**Decisão.** `categoria`/`tag`/`q` são parâmetros GET da rota
`receitas:lista` existente, não rotas dedicadas (`/receitas/categoria/<slug>/`).
**Alternativas.** Views e URLs próprias por categoria e por tag.
**Porquê.** Reaproveita 100% da paginação, do `select_related`/
`prefetch_related` e do template já escritos na spec 002 — filtrar é
"a mesma listagem, com uma `WHERE` a mais", não uma página nova.
**Trade-off.** URL menos "amigável" (`/receitas/?categoria=sobremesas` em
vez de `/receitas/categoria/sobremesas/`); aceitável no escopo educacional
deste projeto.

### ADR-2 — Busca em `icontains` puro, sem normalização de acento

**Decisão.** `Q(titulo__icontains=termo) | Q(ingredientes__icontains=termo)`,
sem tratar acentuação.
**Alternativas.** (a) Normalizar acento em Python antes de comparar (ex.:
`unicodedata.normalize`), filtrando em memória; (b) adotar
`django.contrib.postgres.search` ou `django-watson`.
**Porquê.** `docs/stack.md` já registra a decisão de manter a busca simples
via ORM; a alternativa (a) perderia a vantagem de filtrar no banco (traria
todas as receitas para o Python antes de filtrar) e a (b) está
explicitamente fora de escopo (ver Não-objetivos da spec).
**Trade-off.** Busca não encontra "cenourá" ao digitar "cenoura" — RF-01
já documenta essa limitação explicitamente.

### ADR-3 — Formulário com hidden inputs em vez de re-derivar filtros no template

**Decisão.** `categoria_selecionada`/`tag_selecionada` do contexto viram
`<input type="hidden">` no formulário de busca.
**Alternativas.** Reconstruir a querystring completa manualmente no atributo
`action` do formulário.
**Porquê.** Hidden inputs são o padrão HTML para "preservar estado ao
resubmeter um formulário GET" — mais simples e explícito que montar uma
string de query à mão no template.
**Trade-off.** Nenhum relevante.

## Impacto no código existente

- `receitas/views.py`: `ReceitaListView` ganha `get_queryset()` com
  filtros e `get_context_data()` — método novo, spec 002 só tinha o
  primeiro sem lógica condicional.
- `receitas/templates/receitas/lista.html`: formulário de busca + mensagem
  de estado vazio com contexto (spec 002 já tinha um estado vazio
  genérico; passa a ser condicional ao termo/filtro).
- `templates/includes/cartao_receita.html` e
  `receitas/templates/receitas/detalhe.html`: categoria/tags viram links.
- `templates/includes/paginacao.html`: passa a receber `querystring` do
  contexto.
- `static/css/base.css`: nova classe `.formulario-busca` (layout do
  input+botão) e um ajuste em `.etiqueta` (`text-decoration: none`, agora
  que é um link).

## Estratégia de testes

Reaproveita os builders `_categoria`/`_tag`/`_receita` de `receitas/tests.py`.
Régua nova "Busca e filtros (RF-01 a RF-06, RNF-02)": busca por título,
busca por ingrediente, termo ausente, categoria existente/inexistente, tag
existente/inexistente, combinação busca+categoria, estado vazio com
mensagem, paginação preservando `?categoria=...&page=2` (verificando o
`href` renderizado no HTML da paginação).
