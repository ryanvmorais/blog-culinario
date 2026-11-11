---
feature: Listagem e detalhe público de receitas
status: concluído
date: 2026-09-12
related:
  - 001-modelagem-receitas/requirements.md
origin: concepcao
---

# 002 — Listagem e detalhe público de receitas — design

## Visão geral da abordagem

Duas class-based views em `receitas/views.py` (`ListView` e `DetailView`),
duas rotas em `receitas/urls.py`, dois templates novos, e um include de
cartão de receita compartilhado entre a listagem e a home. A home
(`nucleo`) passa a consultar `Receita` para a seção de destaque.

## Layout de módulos

```
receitas/
  views.py            # ReceitaListView, ReceitaDetailView
  urls.py              # "" -> lista, "<slug>/" -> detalhe
  templates/receitas/
    lista.html
    detalhe.html
templates/includes/
  cartao_receita.html  # usado por lista.html e por nucleo/home.html
  paginacao.html       # controles anterior/próxima
nucleo/
  views.py             # home() ganha `receitas_recentes` no contexto
  templates/nucleo/home.html  # troca os cartões estáticos pelo include
blog_culinario/urls.py # + path("receitas/", include("receitas.urls"))
```

## Componentes

### `ReceitaListView` (RF-01, RF-02, RNF-01)

`ListView` com `paginate_by = 9` e `get_queryset()` filtrando
`publicado=True`, com `select_related("categoria", "autor")` +
`prefetch_related("tags")`. `context_object_name = "receitas"` — o template
itera `receitas`, e o Django já injeta `page_obj`/`paginator` para a
paginação.

### `ReceitaDetailView` (RF-03, RF-04, RNF-01)

`DetailView` com a mesma queryset filtrada/otimizada. O comportamento
padrão do Django (`get_object()` chama `get_queryset()` e filtra por
`slug`, levantando `Http404` se não encontrar) já cobre RF-04 sem código
extra: uma receita não publicada simplesmente não está na queryset, então
seu slug retorna 404 como qualquer slug inexistente.

### `templates/includes/cartao_receita.html` (ADR-3)

Recebe uma `receita` no contexto e renderiza o mesmo `.cartao-receita` que
hoje está hardcoded (com dado placeholder) em `nucleo/home.html`. Mostra
`<img>` quando `receita.imagem_capa` existe; senão, a `<div>` placeholder
que já existe no CSS (mesmo visual, sem foto).

### `templates/includes/paginacao.html`

Recebe `page_obj` e renderiza "Anterior" (se `has_previous`) / indicador de
página / "Próxima" (se `has_next`), usando `.botao--contorno` do design
system existente.

### `nucleo.views.home()` (RF-06)

Passa a consultar as 3 receitas publicadas mais recentes
(`select_related("categoria")`, sem `prefetch_related("tags")` — a home não
exibe tags no cartão) e envia como `receitas_recentes` no contexto. O
template mostra a mensagem de "em breve" quando a lista vier vazia.

## Modelo de dados

Nenhuma mudança — spec consome os models de 001 como estão.

## Interfaces

| Método | URL | View | Nome |
|---|---|---|---|
| GET | `/receitas/` | `ReceitaListView` | `receitas:lista` |
| GET | `/receitas/<slug>/` | `ReceitaDetailView` | `receitas:detalhe` |

`templates/includes/navbar.html` e o botão "Ver receitas" do hero
(`nucleo/templates/nucleo/home.html`) passam a apontar para
`{% url 'receitas:lista' %}` em vez do anchor `#receitas-em-breve`.

## ADRs

### ADR-1 — Class-based views para receitas, function-based para nucleo

**Decisão.** `ReceitaListView`/`ReceitaDetailView` usam `ListView`/
`DetailView`; `nucleo.views.home` continua função.
**Alternativas.** Function-based views para tudo (`get_object_or_404` +
`Paginator` manual).
**Porquê.** É a oportunidade natural de mostrar os dois estilos lado a lado
(o README já promete isso): `ListView`/`DetailView` cobrem paginação e
lookup por slug com muito menos código, e o par function-based (`nucleo`) /
class-based (`receitas`) dá ao leitor os dois modelos mentais no mesmo
repositório.
**Trade-off.** CBVs escondem mais comportamento atrás de métodos herdados;
mitigado com docstring explicando o que cada `get_queryset()` faz e por quê.

### ADR-2 — Paginação por querystring, sem AJAX

**Decisão.** `?page=N` padrão do Django, recarregando a página inteira.
**Alternativas.** Infinite scroll ou paginação via fetch/JS.
**Porquê.** Mantém o projeto sem build step e sem JS além do
`interacoes.js` já existente — consistente com a decisão de frontend da
spec de fundação.
**Trade-off.** Navegação entre páginas de listagem recarrega a página
inteira; aceitável para um blog de conteúdo, não uma SPA.

### ADR-3 — Cartão de receita como include compartilhado

**Decisão.** `templates/includes/cartao_receita.html` recebe `receita` e é
usado tanto por `receitas/lista.html` quanto por `nucleo/home.html`.
**Alternativas.** Duplicar o markup do cartão nos dois templates.
**Porquê.** Os dois lugares renderizam visualmente o mesmo componente — um
include evita que o cartão da home e o da listagem divirjam com o tempo, e
é um exemplo direto de reuso de template no README (`{% include %}`).
**Trade-off.** Nenhum relevante.

## Impacto no código existente

- `nucleo/views.py`: `home()` ganha uma query e um novo item de contexto.
- `nucleo/templates/nucleo/home.html`: a seção "Em breve, receitas de
  verdade" troca os 3 `<article class="cartao-receita">` estáticos por um
  `{% for receita in receitas_recentes %}` com o include, mais o estado
  vazio.
- `templates/includes/navbar.html`: link "Receitas" deixa de estar
  comentado/ausente e passa a apontar para `receitas:lista`.
- `blog_culinario/urls.py`: nova entrada `include("receitas.urls")`.
- CSS/JS do design system: **sem mudança** — `.cartao-receita` e
  `.botao--contorno` já existem e cobrem o que os templates novos precisam.

## Estratégia de testes

`pytest` + `pytest-django`, reaproveitando os builders `_categoria`/`_tag`/
`_receita` de `receitas/tests.py` (spec 001). Grupos novos (réguas `# ---`):
listagem (RF-01, RF-02, com `assertNumQueries` fixado no valor medido, não
estimado, para travar contra regressão de N+1 — RNF-01), detalhe (RF-03,
RF-04), e um teste em `nucleo/tests.py` para a home (RF-06, com e sem
receita publicada).
