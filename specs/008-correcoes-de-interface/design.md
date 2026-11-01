---
feature: Correções da auditoria de interface
status: concluído
data: 2026-10-18
relacionado:
  - 000-fundacao/requirements.md
  - 005-comentarios/requirements.md
origem: concepcao
---

# 008 — Correções da auditoria de interface — design

## Visão geral da abordagem

Quase tudo é CSS e marcação. O CSS segue o que já existe (BEM, tokens em
`tokens.css`, uma folha `base.css`) e ganha duas folhas pequenas: `fontes.css`
(`@font-face` das fontes hospedadas) e nada mais. O único JavaScript novo é o do menu
do celular, dentro do `inicializarMenuMobile()` que já existe. Os textos de teste ficam
em `nucleo/test_interface.py`, um arquivo só para a spec, porque as regras cruzam os
três apps (CSS, base, páginas de erro).

## Layout de módulos

```
static/css/tokens.css        # + --cor-borda-campo, --cor-erro-fundo, bloco do tema escuro
static/css/fontes.css        # novo: @font-face de Fraunces e Inter (latin)
static/css/base.css          # .botao, .estado-vazio, .pagina-formulario, .so-leitor-de-tela,
                             # capa com aspect-ratio, movimento reduzido, alvo da categoria
static/fonts/                # novo: Inter e Fraunces (woff2 variável, subconjunto latin) + licença
static/img/favicon.svg       # novo
static/js/interacoes.js      # menu: foco, Esc, clique fora
templates/base.html          # favicon, fontes locais, bloco `mensagens`
templates/404.html           # novo (herda base.html)
templates/403.html           # novo (herda base.html)
templates/500.html           # novo (HTML completo, sem herança)
templates/includes/          # cartao_receita (link da foto), rodape (texto), mensagens (role)
nucleo/templates/nucleo/home.html
receitas/templates/receitas/{lista,detalhe}.html
usuarios/templates/usuarios/{login,cadastro}.html
receitas/views.py            # contexto do filtro ativo (nome da categoria/tag)
usuarios/forms.py            # autocomplete do e-mail
docs/design-system.html      # catálogo atualizado (RNF-03)
```

## Componentes

### Tokens (`tokens.css`)

- `--cor-borda-campo: #8a7968`: 4,19:1 sobre a superfície branca e 3,83:1 sobre o
  fundo creme. A `--cor-borda` (divisórias, cartões) fica como está (1,24:1 é
  adequado para uma linha decorativa, que não é componente de interface).
- `--cor-erro-fundo: #f8d7da`: o valor cru que estava em `.mensagem--error`.
- Bloco `@media (prefers-color-scheme: dark)` sobrescreve só variáveis de cor, e
  `color-scheme: light dark` no `:root` faz o navegador pintar barras de rolagem e
  controles nativos no tema certo.

### Botão (`.botao`)

`font: inherit` (herda Inter 16 px do corpo, o `<button>` do navegador não herda),
`font-weight: 600` depois dele, `justify-content: center` e `text-align: center`
(rótulo no meio quando a caixa é mais larga que o texto), `min-height: 3rem` (48 px, a
altura que o botão tinha, agora igual para `<a>` e `<button>`). O `.formulario .botao`
ocupa a largura dos campos no celular e, acima de 720 px, tem o tamanho do rótulo
(`min-width: 10rem`), no centro nas páginas de acesso.

### Coluna de formulário (`.pagina-formulario`)

Modificador de `.cabecalho-pagina` para login e cadastro: `max-width` de 460 px
centrada, `h1` e a frase de troca de página com `text-align: center`; `.formulario`
ganha `margin-inline: auto`. Os rótulos continuam à esquerda do campo (leitura de
formulário).

### Estado vazio (`.estado-vazio`)

Parágrafo centrado com `margin-inline: auto` e respiro vertical, usado na home, na
lista e nos comentários.

### Mensagens

`includes/mensagens.html` ganha `role="status"`. O `base.html` envolve a inclusão num
`{% block mensagens %}`; o `detalhe.html` esvazia o bloco e inclui o mesmo parcial dentro
de `#comentarios`, acima do formulário (ADR-2).

### Menu do celular (`interacoes.js`)

`abrirMenu()` e `fecharMenu({ devolverFoco })` substituem o `toggle`: abrir marca
`aria-expanded`, troca o `aria-label` e leva o foco ao primeiro link; Esc fecha e
devolve o foco ao botão; clique fora de `.navbar` fecha sem devolver foco (o visitante
clicou em outro lugar).

### Fontes (`fontes.css`)

`@font-face` de Inter (400 a 700) e Fraunces (400 a 700, eixo `opsz` fixo no padrão),
só o subconjunto `latin` (cobre `ç`, `ã`, `é`). `font-display: swap`. O `base.html`
faz preload da Inter e carrega `fontes.css` antes do `tokens.css`.

## Interfaces

Nenhuma rota nova. Os templates `404.html`, `403.html` e `500.html` são os nomes que o
Django procura sozinho, então não há `handler404` no `urls.py`.

## ADRs

### ADR-1 — Rótulo no centro e botão de formulário proporcional ao tamanho da tela

**Decisão.** `.botao` centraliza o rótulo (`justify-content: center`). O botão de
formulário ocupa a largura dos campos no celular e tem o tamanho do rótulo no computador.
**Alternativas.** (a) largura total em qualquer tela (a primeira versão desta spec);
(b) rótulo à esquerda como estava.
**Porquê.** O defeito inicial era o rótulo fora do centro. A primeira correção deixou o
botão de 420 px com 47 px de texto no `login`, e a medição (`caixa_esticada`, razão 9)
mostrou a desproporção apontada na revisão. No celular a largura total é o alvo de toque
mais fácil; no computador o clique não precisa dela.
**Trade-off.** Duas larguras para o mesmo botão (uma regra `@media`).

### ADR-2 — Mensagem dentro da seção de comentários

**Decisão.** Na página da receita, as mensagens do `django.contrib.messages` aparecem em
`#comentarios`, não no topo.
**Alternativas.** (a) mover o scroll com JavaScript até a mensagem; (b) manter no topo e
redirecionar sem âncora (o visitante perde o lugar).
**Porquê.** O redirect já vai para `#comentarios` (spec 005); a mensagem precisa estar
onde o olho cai. Não precisa de JavaScript.
**Trade-off.** O parcial é incluído em dois lugares (base e detalhe), com o bloco
`mensagens` evitando a duplicação.

### ADR-3 — Tema escuro só por tokens, em commit separado

**Decisão.** `@media (prefers-color-scheme: dark)` redefine variáveis; nenhum seletor de
componente muda. Vai num commit próprio.
**Alternativas.** (a) não ter tema escuro; (b) alternador manual com `data-theme`.
**Porquê.** O design system já isola cor em tokens: é o teste de que a ideia funciona e
custa um bloco de variáveis. Alternador manual precisaria de JavaScript e de
persistência, fora do foco de um projeto de estudo.
**Trade-off.** Sem alternador, quem quer o claro com o sistema escuro não tem como.

### ADR-4 — Fontes hospedadas, só subconjunto `latin`

**Decisão.** Baixar as fontes variáveis do Google Fonts (licença OFL) para `static/fonts/`.
**Alternativas.** (a) manter o link externo; (b) pacote npm das fontes (exigiria build).
**Porquê.** Sem requisição de terceiros (LGPD, o IP do visitante vai ao Google), sem
bloqueio de renderização por CSS externo e sem build. O subconjunto `latin` cobre o
português.
**Trade-off.** Dois arquivos grandes no repositório (uns 100 KB) e a atualização das
fontes passa a ser manual.

### ADR-5 — Estado vazio e coluna de formulário centrados

**Decisão.** O que é curto e isolado fica no centro; o que é leitura (receita,
comentários, rótulos) fica à esquerda.
**Alternativas.** Centrar tudo, ou nada.
**Porquê.** Texto corrido centrado cansa a leitura; um aviso de uma linha ou um
formulário isolado colado à esquerda de uma tela larga parece esquecido.
**Trade-off.** Duas regras de alinhamento para quem edita (documentadas no catálogo).

## Impacto no código existente

- Os testes que procuravam o texto antigo da home não existem (só procuram receitas).
- O `docs/design-system.html` carrega fontes do Google Fonts; passa a carregar
  `fontes.css`.
- O `README.md` mostra `assets/blog-culinario-django-home-receitas-desktop.webp`: a captura é refeita porque a abertura
  da home mudou.

## Estratégia de testes

pytest + client do Django, sem mock. As regras de CSS são lidas do arquivo (o catálogo
já faz o mesmo para contraste) e o contraste é calculado no teste. Cada teste é provado
com a mutação: desfaz-se a correção e o teste precisa falhar.
