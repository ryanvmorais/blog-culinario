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

# 012 — Redesenho da home — design

## Visão geral da abordagem

A view `home` passa a montar tudo o que a página mostra numa quantidade fixa de consultas:
as 4 receitas publicadas mais recentes (a primeira é o destaque, as outras três são as
recentes), as categorias com a contagem de receitas publicadas e as duas contagens da linha
de números. A contagem por categoria vira um método de `QuerySet` de `Categoria`, usado pela
home e pelo rodapé; o rodapé a busca por uma inclusion tag, para que só as páginas que o
mostram façam a consulta e as páginas de erro continuem sem tocar no banco.

O menu do celular é a mesma marcação do menu do desktop: o CSS decide se ela é uma barra
(acima de 720 px) ou um painel lateral (até 720 px). O `interacoes.js` continua dono do
abrir e fechar e passa a cuidar do véu e do `inert`. Nenhum modelo ganha campo, nenhuma
migration nasce e nada novo entra no `pyproject.toml`.

## Layout de módulos

| Arquivo | O que muda |
|---|---|
| `receitas/models.py` | `CategoriaQuerySet.com_receitas_publicadas()`, ligado como manager de `Categoria` (ADR-2) |
| `nucleo/views.py` | `home` monta destaque, recentes, categorias e contagens (ADR-1) |
| `nucleo/templates/nucleo/home.html` | reescrito: abertura, categorias, recentes, "Por dentro" |
| `nucleo/templatetags/navegacao.py` (novo) | `{% link_repositorio %}` e `{% categorias_do_rodape %}` (ADR-3, ADR-8) |
| `templates/includes/navbar.html` | uma marcação para barra e painel, ícones em SVG, véu (ADR-4, ADR-7) |
| `templates/includes/rodape.html` | quatro colunas e o "©" centrado |
| `templates/includes/rodape_categorias.html` (novo) | a lista de categorias do rodapé, usada pela inclusion tag |
| `templates/includes/cartao_receita.html` | sem mudança de marcação; a mesma altura vem do CSS |
| `static/css/tokens.css` | `--cor-veu` (claro e escuro) e `--altura-barra` (ADR-5) |
| `static/css/base.css` | abertura em duas colunas, busca, números, pílula, rótulo, destaque, nota de código, rodapé em colunas, painel do menu, cartão de mesma altura |
| `static/js/interacoes.js` | véu, `inert`, rolagem travada e fechamento pelo véu (ADR-6) |
| `docs/design-system.html` | os componentes novos (RNF-06) |
| `README.md`, `README.en.md` | nada nesta spec |

## Modelo de dados

Sem campo, tabela ou migration. `Categoria` ganha um manager a partir de um `QuerySet`
próprio; o Django não gera migration para manager sem `use_in_migrations = True`.

```python
class CategoriaQuerySet(models.QuerySet["Categoria"]):
    def com_receitas_publicadas(self) -> CategoriaQuerySet:
        return (
            self.annotate(total_receitas=Count("receitas", filter=Q(receitas__publicado=True)))
            .filter(total_receitas__gt=0)
            .order_by("-total_receitas", "nome")
        )
```

## Componentes

### Protótipo validado

O desenho foi validado num protótipo navegável, com o CSS e os tokens do projeto e as
receitas da demonstração, a 390 e a 1280 px. Disposição de cada parte:

```text
1280 px
┌──────────────────────────────────────────────────────────────────────┐
│ Blog Culinário                     Início  Receitas  Entrar  Cadastrar │
├──────────────────────────────────────────────────────────────────────┤
│ (Blog culinário)                         ┌────────────────────────┐   │
│ Receitas simples                         │ capa 4:3 (sem lazy)    │   │
│ para todos os dias.                      ├────────────────────────┤   │
│ descrição                                │ A RECEITA MAIS NOVA    │   │
│ Buscar por título ou ingrediente         │ Shakshuka (h2, link)   │   │
│ [Ex.: cenoura              ] [Buscar]    │ resumo                 │   │
│ 6 receitas · 5 categorias                │ categoria · min · porç.│   │
│ Quer comentar uma receita? Crie sua conta└────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│ POR CATEGORIA / Comece pelo que tem vontade                           │
│ (Pratos principais · 2 receitas) (Lanches · 1 receita) (…)            │
├──────────────────────────────────────────────────────────────────────┤
│ RECÉM-SAÍDAS DO FORNO / Receitas recentes                             │
│ ┌ cartão ┐ ┌ cartão ┐ ┌ cartão ┐   (mesma altura, meta no pé)        │
│               [Ver todas as 6 receitas]                               │
├──────────────────────────────────────────────────────────────────────┤
│ POR DENTRO / Como este blog foi feito                                 │
│ frase de abertura                                                     │
│ ┌ Esta página ┐ ┌ Busca e filtros ┐ ┌ Segurança ┐ ┌ Specs antes … ┐  │
│ │ texto        │ │ texto          │ │ texto     │ │ texto          │  │
│ │ nucleo/views │ │ receitas/views │ │ limitacao │ │ specs/         │  │
│ [Ver o projeto no GitHub]                                             │
├──────────────────────────────────────────────────────────────────────┤
│ Blog Culinário + frase │ NAVEGAR │ CATEGORIAS │ O PROJETO             │
│ ──────────────────────────────────────────────────────────────────── │
│                       © 2026 Blog Culinário                          │
└──────────────────────────────────────────────────────────────────────┘

390 px: abertura centrada, h1 em --texto-2xl, rótulo da busca à esquerda sobre o
campo na largura toda, destaque abaixo do convite; pílulas quebrando linha; cartões
e notas empilhados; rodapé com a marca na largura toda e os links em duas colunas.

390 px, menu aberto:
┌──────────────────────────────┐
│ Blog Culinário            ✕  │  ← barra visível; o botão vira X
├────────┬─────────────────────┤
│ véu    │ Início (atual)      │  ← painel: 80% da largura, até o fim da tela
│        │ Receitas            │
│        │ ─────────────────── │
│        │ SUA CONTA           │
│        │ [Entrar]            │
│        │ [Cadastrar]         │
└────────┴─────────────────────┘
```

### `CategoriaQuerySet` (`receitas/models.py`)

`com_receitas_publicadas()` anota `total_receitas`, descarta as categorias sem receita
publicada e ordena pela contagem e, no empate, pelo nome (RF-06). A home e o rodapé usam o
mesmo método, então as duas listas saem na mesma ordem (RF-12).

### View `home` (`nucleo/views.py`)

Continua uma view de função. Monta o contexto com cinco consultas fixas:

1. `Receita.objects.filter(publicado=True).select_related("categoria")[:4]`, avaliada numa
   lista: `destaque = receitas[0]` e `recentes = receitas[1:]` (ADR-1).
2. `Receita.objects.filter(publicado=True).count()` → `total_receitas`.
3. `list(Categoria.objects.com_receitas_publicadas())` → `categorias`; o total de categorias é
   o `len()` dessa lista, sem consulta a mais.
4. `Comentario.objects.filter(aprovado=True, receita__publicado=True).count()` →
   `total_comentarios`.
5. A inclusion tag do rodapé repete a consulta 3 (ADR-3).

Sessão e usuário (`user`) seguem como hoje, pelo context processor de autenticação.

### `home.html`

Quatro seções, cada uma com a régua de comentário do projeto e `{# fim: NOME #}`:

- **Abertura** (`.hero-dividido`): a coluna de texto (`.hero-dividido__texto`) com a legenda,
  o `h1`, a descrição, o formulário de busca (`action` em `receitas:lista`, `name="q"`), a
  lista de números (`<ul class="numeros">`, cada item só se o número for maior que zero, com
  `pluralize`) e o convite (`{% if not user.is_authenticated %}`); o destaque é um `<article>`
  com a capa dentro de um link `aria-hidden="true" tabindex="-1"` (como o cartão, spec 008,
  RF-02), o rótulo, o `h2` com o link e a meta. O título fica no estilo de link do site
  (`--cor-primaria`, sublinhado), como o título do cartão, para parecer clicável. Sem receita, a classe
  `.hero-dividido--uma-coluna` centra o texto (RF-01).
- **Categorias**: `{% if categorias %}`, um `<ul class="pilulas">` com
  `<a class="pilula" href="{% url 'receitas:lista' %}?categoria={{ slug }}">`.
- **Recentes**: `{% if recentes %}` com a grade e o `include` do cartão, e o botão "Ver todas
  as {{ total_receitas }} receitas"; sem receita publicada, o estado vazio (RF-07).
- **Por dentro**: a frase, as quatro notas em `<ul class="notas-codigo">` (cada `<li>` com
  `h3`, parágrafo e link) e o botão do repositório. Os links das notas saem de
  `{% link_repositorio "nucleo/views.py" %}` (ADR-8).

### Rótulo em caixa alta (`.rotulo`)

Um `<span class="rotulo">` antes do `h2`, fora dele, para o nome da seção no leitor de tela
continuar sendo só o título (RF-11). Cor `--cor-primaria-escura`, `--texto-xs`, peso 700,
caixa alta e `letter-spacing: 0.08em`.

### Pílula de categoria (`.pilula`)

Link com `min-height: 2.75rem`, borda `--cor-borda-campo` (3:1, é componente de interface,
spec 008, RF-08), fundo `--cor-superficie` e a contagem num `<span>` em
`--cor-texto-suave`.

### Cartão de mesma altura

`.cartao-receita` passa a `display: flex; flex-direction: column`, o corpo cresce
(`flex: 1`) e a meta ganha `margin-top: auto` (RF-08). A grade já estica os itens da mesma
linha; a mudança vale na home e na listagem, que usam o mesmo `include`.

### Inclusion tags (`nucleo/templatetags/navegacao.py`)

- `{% link_repositorio caminho %}`: devolve `URL_REPOSITORIO + "/blob/main/" + caminho` para
  arquivo e `"/tree/main/" + caminho` para pasta (caminho que termina em `/`). A base é o
  `URL_REPOSITORIO` que já existe em `blog_culinario/demonstracao.py`.
- `{% categorias_do_rodape %}`: inclusion tag que renderiza
  `includes/rodape_categorias.html` com `Categoria.objects.com_receitas_publicadas()` (ADR-3).

### Rodapé (`includes/rodape.html`)

Grade de quatro colunas (`1.4fr repeat(3, 1fr)`), cada coluna de links num
`<nav aria-labelledby>` com um `h2` pequeno (`--texto-xs`, caixa alta). "Navegar" mostra
Entrar e Cadastrar só sem login. "O projeto" usa `{% link_repositorio %}` para `docs/stack.md`,
`SECURITY.md` e `LICENSE`, e o `URL_REPOSITORIO` puro para "Código no GitHub". Abaixo, o
`<p class="rodape__base">` com borda superior e `text-align: center`. Até 720 px, a marca
ocupa a largura toda e os links ficam em duas colunas (RF-12). O `erro.html` não muda
(RF-13).

### Menu (`includes/navbar.html` e `interacoes.js`)

Marcação única (ADR-4):

```html
<header class="navbar">
  <div class="container">
    <a class="navbar__marca">Blog Culinário</a>
    <button class="navbar__alternador" aria-controls="menu-principal"
            aria-expanded="false" aria-label="Abrir menu de navegação">
      <svg class="icone-menu">…</svg><svg class="icone-fechar">…</svg>
    </button>
    <nav id="menu-principal" class="navbar__painel" aria-label="Navegação principal">
      <ul class="navbar__links">Início, Receitas (aria-current na atual)</ul>
      <div class="navbar__conta">
        <span class="rotulo navbar__rotulo">Sua conta</span>
        Entrar / Cadastrar, ou Olá, nome / Sair (form POST)
      </div>
    </nav>
  </div>
  <div class="navbar__veu" hidden></div>
</header>
```

- **Acima de 720 px:** `.navbar__painel` é uma linha flex com os links e a conta, o rótulo
  "Sua conta" some, o véu e o alternador não aparecem. A barra fica como hoje.
- **Até 720 px:** `.navbar__painel` é `position: fixed`, de `top: var(--altura-barra)` até
  `bottom: 0`, `right: 0`, `width: 80%`, `overflow-y: auto`, fechado com
  `transform: translateX(100%)` e `visibility: hidden`; aberto (`.navbar__painel--aberto`),
  `transform: none` e `visibility: visible`. A transição é só de `transform` (e o
  `visibility` com atraso ao fechar); o bloco de movimento reduzido a desliga (RF-17).
  Os links têm `min-height: 3rem`; a conta tem borda superior, o rótulo e as ações com a
  aparência de botão (contorno para Entrar, primário para Cadastrar) declarada no próprio
  bloco do celular.
- **Ícones:** os dois SVG ficam no HTML e o CSS mostra um ou outro por
  `[aria-expanded="true"]` no botão (ADR-7). Botão de `3rem` x `3rem`.
- **`aria-current="page"`:** o `navbar.html` compara `request.resolver_match.view_name`
  com `nucleo:home` e `receitas:lista`.

`interacoes.js`, `inicializarMenuMobile()`:

- `abrirMenu()`: além do que já faz (classe, `aria-expanded`, `aria-label`, foco no primeiro
  link), mostra o véu (`hidden = false`), põe `inert` em `<main>`, nas mensagens e no rodapé
  e a classe `menu-aberto` no `<html>` (trava a rolagem da página, `overflow: hidden`).
- `fecharMenu({ devolverFoco })`: desfaz os quatro.
- Clique no véu ou num link do painel fecha sem devolver o foco; Esc e o X devolvem.
- Ao passar de 720 px com o menu aberto (`matchMedia(...).addEventListener("change")`), o
  menu fecha, para o `inert` não ficar preso na página do desktop.

## Interfaces

Nenhuma URL nova. Contexto da `home`:

| Chave | Tipo | Conteúdo |
|---|---|---|
| `destaque` | `Receita \| None` | a publicada mais recente |
| `recentes` | `list[Receita]` | até 3, as seguintes ao destaque |
| `total_receitas` | `int` | receitas publicadas |
| `categorias` | `list[Categoria]` | com `total_receitas` anotado, ordem do RF-06 |
| `total_comentarios` | `int` | comentários aprovados em receitas publicadas |

Template tags novas, carregadas com `{% load navegacao %}`: `{% link_repositorio "<caminho>" %}`
e `{% categorias_do_rodape %}`.

## Decisões técnicas (ADRs)

### ADR-1 — Destaque e recentes saem de uma consulta só

**Decisão.** Uma consulta pega as 4 publicadas mais recentes; a primeira é o destaque e as
outras, as recentes.
**Alternativas.** (a) Duas consultas, `.first()` para o destaque e `[1:4]` para as recentes.
(b) Um campo "destaque" no Admin.
**Porquê.** Uma consulta é mais simples e garante que as recentes nunca repitam o destaque.
O campo do Admin foi descartado nos requisitos (decisão resolvida 3).
**Trade-off.** O fatiamento `[0]` e `[1:]` acontece em Python, sobre uma lista de no máximo 4
itens.

### ADR-2 — A contagem por categoria é um método de `QuerySet`

**Decisão.** `CategoriaQuerySet.com_receitas_publicadas()`, exposto como manager de
`Categoria`.
**Alternativas.** (a) A consulta escrita na view e de novo na tag do rodapé. (b) Uma função
solta num módulo `consultas.py`.
**Porquê.** É o lugar idiomático do Django para uma consulta reutilizável, a home e o rodapé
leem a mesma regra e a nota "Esta página" pode apontar o `annotate(Count)` num lugar só.
**Trade-off.** `receitas/models.py` muda, ainda que sem campo nem migration.

### ADR-3 — As categorias do rodapé vêm de uma inclusion tag, não de um context processor

**Decisão.** `{% categorias_do_rodape %}` no `rodape.html`.
**Alternativas.** (a) Context processor com a lista. (b) Context processor com um
`SimpleLazyObject`.
**Porquê.** O context processor roda em todo `render`, inclusive no Admin e nas páginas de
erro, que não podem consultar o banco (spec 008, RF-04); a inclusion tag só consulta quando o
rodapé é desenhado. Também é um exemplo de inclusion tag para quem estuda o projeto.
**Trade-off.** Na home, a lista de categorias é consultada duas vezes (corpo e rodapé): uma
consulta a mais, fixa.

### ADR-4 — Uma marcação para o menu do desktop e o do celular

**Decisão.** O mesmo `<nav>` é barra acima de 720 px e painel até 720 px; o CSS muda a
aparência, inclusive a de botão das ações da conta no celular.
**Alternativas.** (a) Duas marcações, uma escondida em cada largura.
**Porquê.** Links duplicados no HTML são lidos duas vezes por quem desativa o CSS e somam
pontos de manutenção.
**Trade-off.** O bloco do celular repete, nas ações da conta, umas poucas declarações do
`.botao`.

### ADR-5 — A altura da barra vira token

**Decisão.** `--altura-barra: 4.5rem` no `tokens.css`, aplicada ao `.navbar .container` e usada
como `top` do painel e do véu, que são `position: fixed`.
**Alternativas.** (a) Medir a barra em JavaScript. (b) Painel `position: absolute` dentro da
barra, sem chegar ao fim da tela.
**Porquê.** O painel precisa ir da barra até o fim da tela, e só um valor conhecido no CSS
faz isso sem script nem salto quando a página carrega.
**Trade-off.** A barra fica com altura fixa: uma marca maior pede ajustar o token.

### ADR-6 — Fundo inerte pelo atributo `inert`

**Decisão.** Com o menu aberto, `<main>`, as mensagens e o rodapé recebem `inert`, e o
`<html>` a classe `menu-aberto`.
**Alternativas.** (a) `role="dialog"` com `aria-modal="true"` e prisão de foco em JavaScript.
**Porquê.** A barra continua acessível (o X está nela), então o menu não é um diálogo modal; o
`inert` tira o resto da página do Tab e do leitor de tela sem prender o foco à mão.
**Trade-off.** Navegador sem `inert` (anterior a 2023) deixa o fundo alcançável pelo Tab, com
o menu ainda fechando por Esc e pelo véu.

### ADR-7 — Ícones em SVG no HTML, estado só no `aria-expanded`

**Decisão.** Os dois ícones ficam no `navbar.html`, e o CSS mostra um ou outro pelo
`aria-expanded` do botão.
**Alternativas.** (a) O caractere "☰" de hoje e um "✕". (b) Trocar o ícone em JavaScript.
**Porquê.** O caractere muda de desenho conforme a fonte do sistema; o SVG usa
`currentColor` e segue o tema. Um atributo só, que o JavaScript já atualiza, evita estado
duplicado.
**Trade-off.** Um pouco mais de marcação na barra.

### ADR-8 — Os links para o código saem de uma tag, com a base que já existe

**Decisão.** `{% link_repositorio %}` monta o endereço a partir de `URL_REPOSITORIO`
(`blog_culinario/demonstracao.py`), apontando para a branch `main`.
**Alternativas.** (a) Endereços escritos à mão nos templates. (b) Fixar um commit.
**Porquê.** Uma base só, e o teste do RF-10 confere os caminhos contra o repositório. A
`main` mostra o código atual, que é o que a nota descreve.
**Trade-off.** Um fork que mude o nome do repositório troca a constante; o link para a `main`
pode mostrar um arquivo mais novo do que o deploy.

## Impacto no código existente

- **Testes que mudam:** `nucleo/tests.py` (home com até 3 recentes passa a destaque mais 3;
  estado vazio mantido), `nucleo/test_interface.py` (RF-01 da spec 008: o "Por dentro" com
  o título novo, o convite no lugar do botão "Criar minha conta"; o teste do menu do celular
  ganha o véu e o `inert`) e `nucleo/test_descoberta.py` (a frase do rodapé, se a conferir).
- **Specs anteriores:** spec 002, RF-06 e spec 008, RF-01 ganham a linha
  `**Superseded by** 012-redesenho-da-home, RF-07.` e `… RF-04.`, logo abaixo do título.
- **Listagem e detalhe:** herdam o rodapé, o menu e o cartão de mesma altura; nenhum
  template deles muda.
- **Lighthouse CI:** a home já está nos dois JSON de `.github/lighthouse/`; os limites são
  conferidos na implementação.

## Estratégia de testes

Testes com o cliente do Django e o HTML renderizado, como nas specs 002 e 008, num arquivo
novo `nucleo/test_home.py` (RF-01 a RF-11) e em `nucleo/test_menu_e_rodape.py` (RF-12 a
RF-17):

- **Dados:** receitas criadas na hora (publicadas e rascunhos, com e sem capa), categorias
  com e sem receita publicada, comentários aprovados e não aprovados.
- **HTML:** com `html.parser` da biblioteca padrão ou busca de trechos, como os testes
  existentes; o que conta é classe, atributo e texto.
- **Caminhos do "Por dentro" (RF-10):** o teste extrai os links que começam com
  `URL_REPOSITORIO` e confere com `Path` que cada caminho existe a partir da raiz do
  repositório.
- **Consultas (RNF-02):** `django_assert_num_queries` com 1 e com 10 receitas publicadas dá o
  mesmo número.
- **CSS e JS lidos do arquivo** (como o `test_interface.py`): `margin-top: auto` na meta do
  cartão, `transform` no painel, o painel no bloco de movimento reduzido, `inert` e `hidden`
  no `interacoes.js`.
- **Tokens:** o `--cor-veu` tem par no tema escuro (`test_tema_escuro.py`).
- **Navegador real, fora da suíte:** axe-core e as medidas de desenho a 390 e 1280 px, nos dois
  temas, com o menu aberto e fechado (RNF-04), e o Lighthouse CI no PR (RNF-05).

## Desvios

1. **RF-13, componente "Rodapé":** o design dizia que o `erro.html` não mudava. As páginas de erro
   incluíam o mesmo `includes/rodape.html` do resto do site, e o rodapé em colunas lê a sessão
   (Entrar e Cadastrar só sem login) e consulta as categorias. O rodapé de uma linha de antes virou
   `includes/rodape_erro.html` (classe `rodape rodape--linha`), e o `erro.html` passou a incluí-lo.
   O comportamento do RF-13 é o aprovado: página de erro sem categorias, sem sessão e sem banco.
2. **ADR-5:** `--altura-barra` ficou em `4rem` (64 px), não `4.5rem`: cabem o botão de 48 px e
   8 px de cada lado, e a barra do celular não cresce além da de antes. A altura fixa vale só até
   720 px; acima disso a barra continua com a altura do conteúdo, como antes.
3. **RF-10 e a nota "Esta página":** o `annotate(Count)` mora no `CategoriaQuerySet`
   (`receitas/models.py`, ADR-2), não na view. A nota passou a dizer que as categorias vêm "por um
   método de QuerySet com `annotate(Count)`", e o teste do RF-10 confere o `select_related` e a
   chamada `com_receitas_publicadas()` na view e o `annotate(` com `Count(` no modelo.

## Notas de implementação

- **Suíte:** de 375 para 415 testes (`nucleo/test_home.py` e `nucleo/test_menu_e_rodape.py`
  novos, mais os ajustes em `test_interface.py`, `test_tema_escuro.py`, `nucleo/tests.py` e
  `receitas/tests.py`); 3 pulados, como antes. `makemigrations --check`: nenhuma migration.
- **Consultas:** a home faz 5 consultas com 1 ou com 12 receitas (4 da view e 1 do rodapé); a
  listagem passou de 3 para 4, a consulta fixa do rodapé (ADR-3).
- **Navegador real** (Chrome, banco descartável com o `semear_dados_demo`): medidas de desenho
  (`auditar_proporcoes.py`) na home, na listagem e numa receita, a 390 e 1280 px, sem achado
  (rótulo no centro, fonte e altura dos botões). Capturas da home nos dois temas conferidas contra
  o protótipo. Menu a 390 px, nos dois temas: ao abrir, `aria-expanded="true"`, foco em "Início",
  `<main>` inerte e véu visível; o Esc fecha, devolve o foco ao botão e tira o `inert`.
- **axe-core 4.14.0** (MPL-2.0, `axe.min.js` com SHA-256 `20c09fe1…cc46e878`): zero violações na
  home, na listagem e numa receita, a 390 e 1280 px, nos temas claro e escuro, e na home a 390 px
  com o menu aberto, nos dois temas. Nenhuma página rola de lado; cada uma tem um `h1` e nenhum
  pulo de nível nos títulos.
- **Lighthouse CI** (no PR, mobile e desktop): as asserções de `.github/lighthouse/` passaram nas 5
  páginas auditadas, home inclusive, em 15 execuções por perfil.


## Adendo (2026-11-17): página da receita e listagem

> Status do adendo: aprovado (2026-11-17). O texto acima é o aprovado em 2026-11-17 e fica como está; o
> adendo acrescenta o desenho dos RF-19 a RF-28, com os ADRs continuando a numeração.

### Visão geral da abordagem do adendo

A página da receita troca a coluna única por um cabeçalho (capa, categoria, título, resumo,
ficha, autoria e etiquetas) e um corpo em duas colunas acima de 900 px: o cartão de
ingredientes à esquerda, fixo ao rolar, e o modo de preparo à direita, com os passos numerados.
Os passos saem de um método do modelo que divide o texto em parágrafos e separa os numerados,
sem mudar o banco nem montar HTML em Python (ADR-9). Depois dos comentários, a seção "Mais
receitas" vem de uma consulta só, que põe a mesma categoria na frente (ADR-10).

A listagem troca o `.formulario-busca` pela busca da home (`.busca-hero`) e ganha, entre a
busca e a grade, as pílulas da home com a pílula "Todas" e a categoria ativa marcada. As
pílulas leem o mesmo `com_receitas_publicadas()` da home e do rodapé (ADR-2), e o total de
"Todas" é a soma das contagens, sem consulta a mais (ADR-11). Nenhum modelo muda, nenhuma
migration nasce e nenhum token entra: as cores novas reaproveitam pares que já existem.

### Layout de módulos do adendo

| Arquivo | O que muda |
|---|---|
| `receitas/models.py` | `Receita.partes_do_preparo()` e a dataclass `TrechoDoPreparo` (ADR-9) |
| `receitas/views.py` | `ReceitaDetailView` ganha `mais_receitas`; `ReceitaListView` ganha `categorias`, `total_publicadas` e `querystring_sem_categoria` |
| `receitas/templates/receitas/detalhe.html` | Cabeçalho com a ficha, corpo em duas colunas, passos, convite a comentar e "Mais receitas" |
| `receitas/templates/receitas/lista.html` | Busca da home e pílulas de categoria |
| `static/css/base.css` | Seção nova "4.2 Receita e listagem"; o `.formulario-busca` sai, sem uso |
| `docs/design-system.html` | Ficha, cartão de ingredientes, passos, convite a comentar e pílula marcada (RNF-12) |
| `receitas/test_pagina_receita.py`, `receitas/test_listagem.py` | Testes novos (RF-28) |
| `nucleo/test_interface.py`, `receitas/tests.py` | Ajustes onde o HTML ou o CSS antigo era conferido |

### Modelo de dados do adendo

Nenhum campo, nenhuma migration (RNF-07). `TrechoDoPreparo` é uma dataclass só de exibição:

| Campo | Tipo | O que guarda |
|---|---|---|
| `tipo` | `Literal["paragrafo", "passos", "nota"]` | Parágrafo antes ou entre os passos, grupo de passos seguidos, ou parágrafo depois do último passo |
| `textos` | `list[str]` | Os parágrafos do trecho, já sem o número digitado nos passos |
| `inicio` | `int` | Número do primeiro passo do grupo (o `start` do `<ol>`); 1 nos outros tipos |

### Componentes do adendo

#### Protótipo validado do adendo

Validado a 390 e 1280 px com o HTML e o CSS do blog, antes do adendo:

```text
Receita, 1280 px
┌──────────────────────────────────────────────────────────────────────┐
│ capa (largura do container, até 420 px de altura)                    │
│ LANCHES                                                               │
│ Pão de queijo mineiro (h1)                                            │
│ resumo                                                                │
│ ┌ PREPARO │ RENDE      ┐                                              │
│ │ 60 min  │ 10 porções ┘                                              │
│ Por chef-ana · publicado 4 semanas, 2 dias atrás                     │
│ (mineira) (para o lanche)                                             │
│ ┌ Ingredientes ────┐   Modo de preparo                                │
│ │ item             │   (1) Preaqueça o forno a 220 °C.                │
│ │ ──────────────── │   (2) Numa tigela, misture…                      │
│ │ item             │   (3) …                                          │
│ │ (fixo ao rolar)  │   ─────────────────────────                      │
│ └──────────────────┘   nota de fonte, texto menor                    │
│ Comentários                                                           │
│ ┌╌ Ainda não há comentários…            [Entrar para comentar] ╌┐    │
│ CONTINUE COZINHANDO / Mais receitas                                   │
│ ┌ cartão ┐ ┌ cartão ┐ ┌ cartão ┐                                      │
└──────────────────────────────────────────────────────────────────────┘
390 px: uma coluna; o cartão de ingredientes antes do modo de preparo, os passos
numerados, o convite com o botão abaixo do texto, os cartões empilhados.

Listagem, 1280 px (390 px: o mesmo, com as pílulas quebrando linha)
┌──────────────────────────────────────────────────────────────────────┐
│ Receitas (h1)                                                         │
│ Todas as receitas publicadas… (ou "N receitas em X · Limpar filtro")  │
│ Buscar por título ou ingrediente                                      │
│ [Ex.: cenoura              ] [Buscar]                                 │
│ (Todas · 6) (Pratos principais · 2) (Lanches · 1) (…)                 │
│ ┌ cartão ┐ ┌ cartão ┐ ┌ cartão ┐                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### `Receita.partes_do_preparo()` (`receitas/models.py`)

Normaliza as quebras de linha (`\r\n` → `\n`), divide `modo_de_preparo` em parágrafos pelos
blocos separados por linha em branco e descarta os vazios. Um parágrafo é passo quando casa
com `^\s*\d+[.)]\s+`; o número digitado sai do texto. Os passos seguidos formam um trecho
`passos`, numerado pela posição (o primeiro passo da receita é 1, mesmo que o texto diga
outro número), e um parágrafo sem número entre dois grupos fica entre eles, com o segundo
grupo continuando a contagem (`inicio`). Os parágrafos depois do último passo viram `nota`.
Sem nenhum passo, devolve um único trecho `paragrafo` com todos os parágrafos (RF-22). Não
grava nada e não monta HTML (ADR-9).

#### Ficha e autoria (`detalhe.html`)

`<dl class="ficha">` com dois `<div>`, cada um com `<dt>` ("Preparo", "Rende") e `<dd>`
("{{ tempo_preparo_minutos }} min"; porções com `pluralize:"ão,ões"` sobre "porç"). Logo
abaixo, `<p class="receita-autoria">` com "Por {{ autor }} · publicado {{ criado_em|naturaltime }}"
e "Autor removido" sem autor. As etiquetas continuam no `<ul class="etiquetas">` de hoje (RF-19).

#### Corpo em duas colunas (`.receita-corpo`)

`<div class="receita-corpo">` com o `<section class="ingredientes" aria-labelledby>` e o
`<section class="preparo" aria-labelledby>`, nessa ordem no HTML, que é a ordem do celular e
do leitor de tela. Acima de 900 px, `grid-template-columns: 22rem minmax(0, 1fr)` (ADR-13).
O cartão de ingredientes tem `position: sticky`, `top` igual à altura da barra mais
`--espaco-6`, `max-height` da tela menos essa folga e `overflow-y: auto`, com `tabindex="0"`
para a rolagem interna funcionar pelo teclado (ADR-12). Os ingredientes saem de
`ingredientes.splitlines`, sem as linhas vazias, numa `<ul>` sem marcador e com divisória
`--cor-borda` entre os itens (RF-20, RF-21).

#### Passos (`.passos`)

O template percorre `partes_do_preparo`: `paragrafo` vira `<p>`, `passos` vira
`<ol class="passos" start="{{ inicio }}">` com um `<li>` por passo, e `nota` vira
`<p class="preparo-nota">`, com a linha de cima e o texto em `--texto-sm` e
`--cor-texto-suave`. Cada texto passa por `linebreaksbr`, que escapa o HTML como o
`linebreaks` de hoje. O número do passo é um `::before` com `counter(list-item)`, num círculo
com `--cor-primaria-clara` e `--cor-primaria-escura`, o par da legenda da home; o leitor de
tela anuncia a lista ordenada pelo `<ol>` (RF-22, RNF-10).

#### Convite a comentar (`.convite-comentar`)

Para anônimo, no fim da seção "Comentários": um `<div class="convite-comentar">` com borda
tracejada `--cor-borda-campo`, a frase ("Ainda não há comentários. Seja o primeiro a
comentar!" sem comentários; "Entre para deixar um comentário." com eles) e o
`<a class="botao botao--contorno">` "Entrar para comentar", para o login com
`?next=<caminho da receita>`, o mesmo destino do link de hoje. Para autenticado, a seção não
muda (RF-23).

#### "Mais receitas" (`ReceitaDetailView`)

`get_context_data` acrescenta `mais_receitas`: as publicadas, sem a aberta, com
`select_related("categoria")`, anotadas com `mesma_categoria = Case(When(categoria_id=…,
then=0), default=1)` e ordenadas por `mesma_categoria` e `-criado_em`, cortadas em 3 (ADR-10).
O template mostra a seção com `.rotulo` "Continue cozinhando", o `h2` "Mais receitas" e os
cartões de `includes/cartao_receita.html`, que já carregam a capa com `loading="lazy"`; com a
lista vazia, a seção some (RF-24, RNF-11).

#### Busca da listagem (`lista.html`)

O formulário passa a ser `.busca-hero` (rótulo, `.busca-hero__linha` com o campo e o botão),
com os campos ocultos de categoria e tag de hoje. Na listagem, `.lista-cabecalho
.busca-hero` tira a margem automática, para a busca ficar à esquerda; a largura máxima de
34rem é a da home (RF-25).

#### Pílulas da listagem

`<nav class="lista-categorias" aria-label="Categorias">` com o `<ul class="pilulas">` da
home. A primeira pílula é "Todas · {{ total_publicadas }}"; as outras, as `categorias` da
view. Cada `href` é `?{{ querystring_sem_categoria }}&categoria=<slug>` (sem o `&` quando a
querystring está vazia); "Todas" leva só a `?{{ querystring_sem_categoria }}`, ou à listagem
sem parâmetros. A pílula ativa ganha `aria-current="page"` e, no CSS, `--cor-primaria` de
fundo, `--cor-texto-invertido` no texto e na contagem, o par do `.botao--primario`. Sem
categorias, o `<nav>` não aparece (RF-26).

#### Contexto da listagem (`ReceitaListView`)

`get_context_data` acrescenta `categorias` (lista de `com_receitas_publicadas()`),
`total_publicadas` (soma de `total_receitas` das categorias, ADR-11) e
`querystring_sem_categoria` (o `GET` sem `page` e sem `categoria`, urlencoded). O
`paginate_by = 9` não muda (RF-27).

### Interfaces do adendo

Nenhuma URL nova. A listagem continua aceitando `q`, `categoria`, `tag` e `page` (spec 003); as
pílulas só montam links com esses parâmetros.

### ADR-9 — Os passos saem de um método do modelo, sem HTML em Python

**Decisão.** `Receita.partes_do_preparo()` devolve uma lista de `TrechoDoPreparo` com textos
puros; o template monta o `<ol>` e escapa cada texto com `linebreaksbr`.
**Alternativas.** (a) Um filtro de template que devolve o HTML pronto, com `mark_safe`. (b) Um
campo por passo, com migration e inline no Admin. (c) Só CSS, contando os `<p>` de hoje.
**Porquê.** O método é uma função pura, testável sem banco e sem template, e o escape fica com
o Django, como hoje. (a) põe HTML montado à mão num lugar onde um esquecimento vira XSS; (b)
foi descartada nos requisitos (decisão resolvida 5); (c) não tira o número digitado do texto.
**Trade-off.** A regra "parágrafo que começa por número é passo" fica implícita para quem
escreve no Admin. Mudar o `help_text` do campo para explicá-la geraria migration (RNF-07), então
ela fica documentada aqui e no teste.

### ADR-10 — "Mais receitas" numa consulta, com `Case`/`When`

**Decisão.** Uma consulta anota `mesma_categoria` com `Case(When(...))` e ordena por ela e
pela data.
**Alternativas.** (a) Duas consultas: a mesma categoria e, se faltar, as outras. (b) Um método
em `QuerySet` de `Receita`, como o `CategoriaQuerySet` da ADR-2.
**Porquê.** Uma consulta cobre o "primeiro a mesma categoria, depois as outras" sem lógica de
completar em Python, nunca repete receita e mostra a quem estuda uma expressão condicional do
ORM. (b) não se paga com um só uso; se outra página precisar da regra, ela sobe para o modelo.
**Trade-off.** A ordenação por um campo anotado percorre todas as receitas publicadas antes do
corte em 3; no tamanho de um blog, não pesa.

### ADR-11 — O total de "Todas" é a soma das contagens

**Decisão.** `total_publicadas = sum(c.total_receitas for c in categorias)`.
**Alternativas.** (a) `Receita.objects.filter(publicado=True).count()`. (b) O `paginator.count`.
**Porquê.** `Receita.categoria` é obrigatória (`on_delete=PROTECT`, sem `null`), então toda
receita publicada está numa categoria e a soma é o total, sem consulta a mais (RNF-08). (b)
muda com a busca, e o RF-26 pede o total sem considerar a busca.
**Trade-off.** Se um dia a categoria virar opcional, a soma deixa de fora as receitas sem
categoria; o teste do RF-26 compara a soma com o `count()` e acusa a diferença.

### ADR-12 — Ingredientes fixos com `position: sticky` e rolagem própria

**Decisão.** `position: sticky` com `max-height` e `overflow-y: auto` no cartão, que leva
`tabindex="0"`.
**Alternativas.** (a) `sticky` sem limite de altura. (b) JavaScript que fixa o cartão.
**Porquê.** Sem limite (a), um cartão mais alto que a tela esconde os últimos ingredientes até
o fim dos passos, contra o RF-21; o CSS resolve sem script (b), e o CSP fica como está. O
`tabindex="0"` deixa a rolagem interna ao alcance do teclado, que o axe exige de região rolável.
**Trade-off.** Uma parada de Tab a mais na página, no cartão, mesmo quando ele não rola.

### ADR-13 — Duas colunas a partir de 900 px

**Decisão.** Uma `@media (min-width: 900px)` nova, só para o corpo da receita.
**Alternativas.** (a) O ponto de quebra de 721 px que o resto do site usa. (b) Um token.
**Porquê.** Entre 721 e 900 px, com 22rem de ingredientes, o modo de preparo ficaria com menos
de 380 px, mais estreito que no celular. (b) não funciona: variável CSS não vale dentro de
`@media`.
**Trade-off.** O CSS passa a ter dois pontos de quebra de largura; o novo vale só para esta
página.

### Impacto no código existente do adendo

- **`detalhe.html`** é reescrito do cabeçalho até o fim da seção de comentários; o formulário
  de comentário (spec 005, spec 007) e a lista de comentários não mudam.
- **`.formulario-busca`** sai do `base.css`: a listagem era o único uso. O teste do token de
  borda de campo em `nucleo/test_interface.py` passa a conferir o campo da `.busca-hero`, que já
  usa `--cor-borda-campo`.
- **Testes de HTML** em `receitas/tests.py` que procuram o link "Entre" ou a lista de
  ingredientes antiga são ajustados ao HTML novo, sem perder o que conferem.
- **Consultas:** a listagem passa de 4 para 5 (as pílulas); a página da receita ganha 1 ("Mais
  receitas"). As duas continuam fixas (RNF-08).
- **Lighthouse CI:** as duas páginas já estão em `.github/lighthouse/`; os limites são
  conferidos no PR (RNF-11).

### Estratégia de testes do adendo

- **Unidade, sem banco** (`receitas/test_pagina_receita.py`): `partes_do_preparo()` com passos
  "1." e "1)", parágrafo antes, entre e depois dos passos, numeração pela posição, `\r\n`,
  parágrafos vazios e o caso sem passo (RF-22).
- **Integração, com o `Client`:** a receita (ficha com plural e singular, autoria e "Autor
  removido", cartão de ingredientes sem linha vazia, `<ol>` com `start`, nota, convite para
  anônimo com e sem comentários, seção de hoje para autenticado, "Mais receitas" com a mesma
  categoria primeiro, complemento, sem a aberta, limite de 3 e ausência) e a listagem
  (`receitas/test_listagem.py`: busca com os ocultos, pílulas na ordem com "Todas", contagens
  que ignoram a busca, `aria-current`, links com `q` e `tag` e sem `page`, ausência sem
  categorias, soma igual ao `count()`, paginação com 9).
- **Consultas:** `assertNumQueries` com 2 e com 12 receitas, nas duas páginas (RNF-08).
- **CSS lido do arquivo:** o `sticky` com `max-height` e `overflow-y`, o ponto de 900 px e a
  pílula marcada só com tokens (`nucleo/test_interface.py`); os pares de contraste em
  `nucleo/test_tema_escuro.py` (RNF-09).
- **No navegador** (fora da suíte, registrado nas notas): axe-core e medidas de desenho nas
  duas páginas, a 390 e 1280 px, nos dois temas, e o cartão fixo ao rolar (RNF-10).

### Desvios do adendo

1. **RF-26:** a região das pílulas se chama "Filtrar por categoria", não "Categorias". O rodapé
   já tem uma região de navegação "Categorias" (RF-12), e o axe-core acusou dois marcos com o
   mesmo nome (`landmark-unique`): o leitor de tela não distinguiria um do outro. O
   comportamento do RF-26 é o aprovado: uma região de navegação com nome, com as pílulas.
2. **Componente "Corpo em duas colunas" e "Passos":** a `.receita-corpo` e a `.passos` ganharam
   `grid-template-columns: minmax(0, 1fr)` também no celular. Sem a coluna explícita, uma grade
   cresce até o maior conteúdo e passa da largura da tela: foi o defeito encontrado na abertura
   da home, corrigido à parte.

### Notas de implementação do adendo

- **Suíte:** de 416 para 462 testes (`receitas/test_pagina_receita.py` e
  `receitas/test_listagem.py` novos, mais os ajustes em `nucleo/test_interface.py`,
  `nucleo/test_tema_escuro.py` e `receitas/tests.py`); 3 pulados, como antes.
  `makemigrations --check`: nenhuma migration; o `total_receitas: int` em `Categoria` é só a
  anotação de tipo para o mypy.
- **Consultas:** a listagem passou de 4 para 5 (as pílulas) e a receita ganhou 1 ("Mais
  receitas"); as duas são iguais com 2 e com 12 receitas.
- **Navegador real** (Chrome, servidor local com os dados da demonstração): nenhuma rolagem
  lateral na receita, na listagem e na listagem filtrada a 320, 360, 390, 412 e 1280 px, com a
  fonte normal e 30% maior. O cartão de ingredientes fica a 88 px do topo ao rolar passos
  longos e, com 48 ingredientes, limita-se à altura da tela e rola por dentro.
- **axe-core 4.14.0** (mesmo SHA-256 da spec): zero violações na receita, na listagem e na
  listagem filtrada, a 390 e 1280 px, nos temas claro e escuro, depois do desvio 1. Nenhum alvo
  de toque menor que 24 px; todas as paradas de Tab com indicador visível.
- **Medidas de desenho** (`auditar_proporcoes.py`): botões sem achado. Duas sugestões de
  alinhamento ficam como estão por decisão aprovada: a busca da listagem à esquerda (RF-25) e o
  aviso de comentários à esquerda no cartão (spec 008, RF-17).
