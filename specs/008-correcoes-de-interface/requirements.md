---
feature: Correções da auditoria de interface
status: concluído
date: 2026-10-18
related:
  - 000-fundacao/requirements.md
  - 005-comentarios/requirements.md
origin: concepcao
---

# 008 — Correções da auditoria de interface

## Contexto e problema

Em 18/10/2026 a auditoria de interface mediu 14 telas em navegador real (390 e
1280 px, tema claro e escuro do sistema, axe-core 4.14.0, teclado, comentário,
cadastro com erros e uma capa de receita atrasada). A base é sólida (todo texto
passa de 4,5:1, nenhuma tela rola de lado, todas as paradas de Tab têm indicador de
foco), mas apareceram 11 falhas objetivas, 5 escolhas de gosto e, numa segunda
passada pedida pelo mantenedor, dois defeitos de **proporção e alinhamento** que o axe não
vê: o rótulo dos botões de largura total fica colado à esquerda (24 px de folga de um
lado e 239 a 355 px do outro) e os `<button>` saem em Arial 13 px, enquanto o resto do
site usa Inter 16 px; e textos curtos (estados vazios, formulários de acesso) ficam à
esquerda onde o resto da página é centrado.

Além disso, a home abre falando do Django ("Código limpo para quem quer dominar o
Django"), quando a intenção do projeto é ser, por fora, um blog culinário e, por dentro,
um projeto Django aberto para estudo.

## Objetivos

- Corrigir as 11 falhas objetivas, aplicar as 5 escolhas com a opção recomendada e
  corrigir proporção e alinhamento dos botões e dos textos curtos.
- A home fala de receitas; o Django aparece como "por dentro", numa seção própria.
- Cada correção com teste que falha quando ela é desfeita.

## Não-objetivos

- Trocar a identidade visual (paleta, tipografia, espaçamento) além dos tokens novos.
- Introduzir framework de CSS ou etapa de build: o projeto continua CSS puro.
- Mexer no `#f8d7da` e nos três tokens sem uso que o catálogo já registrava: o
  `#f8d7da` vira o token `--cor-erro-fundo` só porque o tema escuro exige.
- Reescrever o resto dos textos do site: só a home e o rodapé.

## Personas

- Como **visitante de teclado ou leitor de tela**, quero chegar ao menu, ao
  comentário e à ajuda dos campos sem tropeçar em links vazios ou ids que não existem.
- Como **visitante no celular**, quero botões com o rótulo no meio e a página sem
  saltos quando a foto chega.
- Como **aprendiz de Django**, quero perceber que o blog é um projeto real e achar o
  código sem que a home pareça um site de venda de curso.

## Requisitos funcionais

### RF-01 — Home: blog por fora, Django por dentro

- **Given** um visitante abre a home
  **When** a página carrega
  **Then** o título da abertura fala de receitas, o botão principal leva à lista e
  não há menção ao Django no `h1`.
- **Given** a mesma página
  **When** o visitante rola até o fim
  **Then** uma seção "Por dentro" explica em poucas linhas que o blog é um projeto
  Django educacional e aberto, com o link para o repositório.
- **Given** o visitante não está autenticado
  **When** vê a abertura
  **Then** o segundo botão convida a criar conta (quem já entrou não vê botão
  secundário).

### RF-02 — Um link por cartão para teclado e leitor de tela

- **Given** um cartão de receita (home e lista)
  **When** o visitante percorre a página com Tab
  **Then** o link da foto não recebe foco nem é lido (`aria-hidden="true"` e
  `tabindex="-1"`); a categoria e o título continuam sendo links, e o axe não
  acusa `link-name`.

### RF-03 — Hierarquia de títulos da lista

- **Given** a lista de receitas
  **When** a página é lida por estrutura
  **Then** entre o `h1` e os títulos `h3` dos cartões existe um `h2` visualmente
  oculto ("Lista de receitas"), sem pulo de nível.

### RF-04 — Páginas de erro do projeto

- **Given** `DEBUG=False`
  **When** o visitante abre um endereço inexistente (404), sem permissão (403) ou o
  servidor falha (500)
  **Then** vê uma página em português, com `lang`, `viewport`, `<main>` e links de
  volta, não a página padrão do Django em inglês.
- **Given** o 500
  **When** a página é renderizada
  **Then** ela não depende de banco, de sessão nem de contexto (herda nada do
  `base.html`).

### RF-05 — Mensagem ao lado da ação

- **Given** o visitante envia um comentário
  **When** a página volta com a mensagem
  **Then** a mensagem aparece dentro da seção de comentários, acima do formulário,
  com `role="status"`, e fica visível na tela depois do redirect para `#comentarios`.
- **Given** qualquer outra página com mensagem (login, cadastro, saída)
  **When** ela carrega
  **Then** a mensagem continua no topo, agora com `role="status"`.

### RF-06 — Menu do celular por teclado

- **Given** o menu do celular
  **When** é aberto pelo botão (clique, Enter ou Espaço)
  **Then** o foco vai para o primeiro link, o botão troca o `aria-label` para
  "Fechar menu de navegação" e `aria-expanded` vira `true`.
- **Given** o menu aberto
  **When** o visitante aperta Esc
  **Then** o menu fecha e o foco volta ao botão.
- **Given** o menu aberto
  **When** o visitante clica fora da barra
  **Then** o menu fecha (sem roubar o foco).

### RF-07 — Cadastro: ajuda ligada aos campos

- **Given** o formulário de cadastro
  **When** é renderizado
  **Then** todo `aria-describedby` aponta para um id que existe, o texto de ajuda não
  é um `<p>` com `<ul>` dentro (HTML inválido) e a lista de regras da senha herda o
  estilo da ajuda; o campo de e-mail declara `autocomplete="email"`.

### RF-08 — Borda dos campos com contraste

- **Given** campos de texto, busca e comentário
  **When** a borda é comparada com o fundo da página e com a superfície do campo
  **Then** o contraste é de pelo menos 3:1 (WCAG 1.4.11), nos temas claro e escuro,
  por um token próprio (`--cor-borda-campo`) que não altera as linhas divisórias.

### RF-09 — A capa não empurra o texto

- **Given** a página de uma receita com foto
  **When** a foto chega depois do texto
  **Then** o espaço dela já estava reservado (`aspect-ratio`), e o deslocamento de
  layout (CLS) da página é menor que 0,1.

### RF-10 — Botões: fonte, proporção e rótulo no centro

- **Given** qualquer `.botao` (`<a>` ou `<button>`)
  **When** é medido no navegador
  **Then** usa a fonte do corpo (Inter), no mínimo o tamanho do corpo, tem altura de
  2,2 a 3,8 vezes o corpo da letra e o rótulo está no centro da caixa (diferença de
  até 3 px entre a folga da esquerda e a da direita), inclusive em largura total.
- **Given** dois botões com as mesmas classes, um `<a>` e um `<button>`
  **When** são comparados
  **Then** têm a mesma fonte e a mesma altura.
- **Given** um botão de envio de formulário
  **When** a tela tem mais de 720 px
  **Then** ele tem o tamanho do rótulo (no centro da coluna nas páginas de acesso, à
  esquerda no comentário); no celular ocupa a largura dos campos.

### RF-11 — Movimento reduzido

- **Given** o sistema pede "reduzir movimento"
  **When** o visitante usa âncoras ou passa o mouse nos cartões e botões
  **Then** não há rolagem suave, elevação do cartão nem transição de cor.

### RF-12 — Ícone da aba

- **Given** qualquer página
  **When** o navegador procura o ícone
  **Then** encontra `<link rel="icon">` apontando para um SVG do projeto, e não gera
  404 em `/favicon.ico`.

### RF-13 — Filtro ativo à vista

- **Given** a lista com `?categoria=`, `?tag=` ou `?q=`
  **When** a página carrega
  **Then** a frase de abertura diz o resultado ("4 receitas em **Sobremesas**") e um
  link "Limpar filtro" leva à lista completa; sem filtro, a frase segue a de hoje.

### RF-14 — Fontes hospedadas no projeto

- **Given** qualquer página
  **When** o navegador monta o `<head>`
  **Then** nenhuma requisição vai ao Google Fonts: Fraunces e Inter vêm de
  `static/fonts/`, com `font-display: swap` e o preload da fonte do corpo.

### RF-15 — Tema escuro do sistema

- **Given** o sistema operacional está em tema escuro
  **When** o visitante abre qualquer página
  **Then** o site usa a paleta escura definida só por tokens, com todo texto acima de
  4,5:1 e os botões e links legíveis; no tema claro nada muda.

### RF-16 — Alvo de toque da categoria

- **Given** o selo de categoria do cartão e da receita
  **When** é medido
  **Then** o alvo de clique tem pelo menos 24 px de altura (WCAG 2.5.8).

### RF-17 — Alinhamento do que é curto

- **Given** as páginas de entrar e criar conta
  **When** abrem no computador
  **Then** a coluna do formulário (título, campos, botão e a frase de troca de
  página) fica centrada na tela, com o título e a frase centrados e os rótulos dos
  campos à esquerda.
- **Given** um estado vazio da lista ("Nenhuma receita publicada ainda", busca sem
  resultado)
  **When** é exibido
  **Then** o texto fica centrado dentro de um bloco com respiro, não colado à
  esquerda de uma área larga.
- **Given** o aviso "Ainda não há comentários"
  **When** é exibido
  **Then** segue o alinhamento do título "Comentários" que o abre (à esquerda): o
  aviso que acompanha um título não muda de lado sozinho.

## Requisitos não-funcionais

### RNF-01 — Sem dependência nova

Nada de biblioteca nem de etapa de build. As fontes são arquivos estáticos; o JS
continua vanilla.

### RNF-02 — Tudo por tokens

Nenhuma cor nem tamanho "cru" novo fora do `tokens.css`: o tema escuro e a borda dos
campos entram como variáveis.

### RNF-03 — Catálogo em dia

O `docs/design-system.html` mostra o que mudou (token novo, botões, estado vazio,
hero, tema escuro) e a tabela de contraste inclui os pares do tema escuro.

## Decisões resolvidas

1. **Favicon (RF-12):** desenho simples (tigela creme sobre quadrado terracota)
   escolhido a pedido do mantenedor; é fácil de trocar (um arquivo SVG).
2. **Tema escuro (RF-15):** aplicado como o mockup da auditoria (só tokens), em
   commit separado para ser fácil de remover.
3. **Botões de formulário (RF-10):** o rótulo fica sempre no centro da caixa. No
   celular o botão ocupa a largura dos campos (alvo de toque); no computador, depois
   da medição mostrar um botão de 420 px para um rótulo de 47 px, passou a ter o
   tamanho do rótulo.

## Testes

Cobertura planejada, uma por requisito (etapa própria em `tasks.md`):

- HTML renderizado: cartão, lista, 404/403/500, mensagem, cadastro, home, filtro,
  estado vazio, favicon e ausência do Google Fonts.
- CSS e tokens lidos do arquivo: `font: inherit` e `justify-content: center` no
  `.botao`, `aspect-ratio` da capa, bloco de movimento reduzido, contraste calculado
  da borda dos campos e dos pares do tema escuro.
- JavaScript: marcadores do comportamento do menu (Esc, foco, clique fora).
- Verificação em navegador real (fora do pytest): axe, percurso de Tab, CLS e a
  `auditar_proporcoes.py` antes e depois, registradas em `tasks.md`.
