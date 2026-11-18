---
feature: Redesenho da home
status: concluído
date: 2026-11-17
related:
  - 002-listagem-detalhe-receitas/requirements.md
  - 003-busca-e-filtros/requirements.md
  - 005-comentarios/requirements.md
  - 008-correcoes-de-interface/requirements.md
origin: concepcao
---

# 012 — Redesenho da home

## Contexto e problema

A home tem três blocos: uma abertura com título, texto e dois botões ("Ver receitas" e
"Criar minha conta"), as 3 receitas mais recentes (spec 002, RF-06) e o painel "Por
dentro, um projeto Django" (spec 008, RF-01), que diz em um parágrafo que o blog é material
de estudo e leva ao repositório. O rodapé é uma linha só.

Comparada às homes de blogs de receitas bem avaliados, ela deixa de fora o que quase todos
oferecem logo de cara:

- **Busca na abertura.** Cinco de sete homes consultadas põem a busca no topo; aqui ela só
  existe na listagem (spec 003).
- **Entrada por categoria.** Quatro de sete mostram as categorias na home, algumas com a
  contagem de receitas; aqui a categoria só aparece dentro de cada cartão.
- **Uma receita em destaque.** Quatro de sete abrem com um prato grande; aqui a primeira tela
  só tem texto.

Fontes: [Smitten Kitchen](https://smittenkitchen.com), [Minimalist Baker](https://minimalistbaker.com),
[Pinch of Yum](https://pinchofyum.com), [Love and Lemons](https://www.loveandlemons.com),
[Panelinha](https://panelinha.com.br), [Tudo Gostoso](https://www.tudogostoso.com.br),
[Receitas Nestlé](https://www.receitasnestle.com.br) e o artigo da
[Feast Design Co.](https://feastdesignco.com/rethinking-the-homepage/), consultados em 2026-11-17.

O lado educacional também rende pouco: "Por dentro" afirma que há uma aplicação Django
completa, mas não mostra onde está nenhuma parte dela. E no celular o menu aberto não troca
o ícone por um X, e a página continua visível logo abaixo do último link, como se fosse
parte do menu.

O desenho foi validado num protótipo navegável a 390 e 1280 px, com as receitas da
demonstração, antes desta spec. Esta spec substitui, quando concluída: spec 002, RF-06
(primeiro cenário, "até 3 receitas"); spec 008, RF-01 (terceiro cenário, o botão secundário
da abertura).

## Objetivos

- Dar três entradas para achar uma receita na primeira tela: a busca, a categoria e a
  receita mais nova.
- Mostrar na abertura só números contados dos dados publicados.
- Fazer "Por dentro" apontar, para cada parte do blog, o arquivo que a faz funcionar.
- Dar ao rodapé navegação, categorias e os documentos do projeto, em todas as páginas.
- Fazer o menu do celular parecer um menu: X para fechar, por cima da página escurecida.

## Não-objetivos

- **Modelo e Admin:** nenhum campo novo e nenhuma migration. O destaque é a receita mais nova,
  não uma escolha no Admin.
- **Listagem e detalhe da receita:** só herdam o cartão de mesma altura (RF-08), o rodapé e
  o menu.
  **Superseded by** adendo, RF-19 a RF-27.
- **Menu do desktop:** a barra com os links continua como está.
- **Recursos comuns em blogs de receitas que não entram:** newsletter (o blog não envia
  e-mail), carrossel, avaliação em estrelas, "mais populares" e receitas da época (com poucas
  receitas, repetiriam as mesmas na página).
- **Receita aleatória e filtro por tempo de preparo:** são desafios propostos no README para
  quem estuda o projeto.
- **Paleta, fontes e tokens existentes:** não mudam; entra só o token do véu do menu
  (RNF-03).

## Personas

- Como **visitante com fome**, quero achar em segundos uma receita pela busca, pela categoria
  ou pela foto, sem rolar a página.
- Como **quem estuda Django**, quero saber, pela home, em que arquivo está cada parte do blog
  e por onde começar a ler.
- Como **visitante no celular**, quero perceber que o menu abriu e fechá-lo pelo mesmo botão.
- Como **visitante de teclado ou leitor de tela**, quero os títulos em ordem, um link por
  cartão e o menu com nome e estado anunciados.

## Requisitos funcionais

### Abertura

### RF-01 — Abertura em duas colunas no desktop, centrada no celular

- **Given** a home acima de 720 px, com receita publicada
  **When** a página abre
  **Then** a abertura tem duas colunas: à esquerda, a legenda "Blog culinário", o `h1`
  "Receitas simples para todos os dias.", a descrição, a busca (RF-02), os números (RF-03) e
  o convite à conta (RF-04), alinhados à esquerda; à direita, a receita em destaque (RF-05).
- **Given** a home até 720 px
  **When** a página abre
  **Then** a abertura tem uma coluna, com o texto centrado e o `h1` no mesmo tamanho de hoje
  (`--texto-2xl`), e a receita em destaque vem logo abaixo do convite à conta.
- **Given** nenhuma receita publicada
  **When** a home abre, em qualquer largura
  **Then** a abertura tem uma coluna, com o texto centrado.

### RF-02 — Busca na abertura

- **Given** a abertura
  **When** a página abre
  **Then** há um formulário de busca (`role="search"`, método GET) com o rótulo visível
  "Buscar por título ou ingrediente", o campo `q` com o exemplo "Ex.: cenoura" e o botão
  "Buscar".
- **Given** o visitante digita um termo e envia
  **When** o formulário é enviado
  **Then** a listagem de receitas abre com a busca aplicada, como a busca da própria listagem
  (spec 003).
- **Given** a abertura centrada do celular
  **When** a página abre
  **Then** o rótulo fica à esquerda, sobre o campo na largura toda (spec 008, RF-17: rótulo
  de campo é leitura).

### RF-03 — Números contados dos dados

- **Given** receitas publicadas, categorias com receita publicada e comentários aprovados em
  receitas publicadas
  **When** a home abre
  **Then** abaixo da busca aparece a linha "N receitas · N categorias · N comentários", com os
  números contados do banco e o singular para 1 ("1 receita", "1 categoria", "1 comentário").
- **Given** uma das contagens igual a zero
  **When** a home abre
  **Then** aquele número some da linha; com as três em zero, a linha não aparece.
- **Given** o `home.html`
  **When** se procura um número escrito no template
  **Then** nada é encontrado: todo número da linha vem da view.

### RF-04 — Convite à conta

**Substitui** spec 008, RF-01, terceiro cenário.

- **Given** um visitante não autenticado
  **When** a home abre
  **Then** abaixo dos números aparece "Quer comentar uma receita? Crie sua conta.", com "Crie
  sua conta." levando ao cadastro; não há botão "Criar minha conta" na abertura.
- **Given** um visitante autenticado
  **When** a home abre
  **Then** o convite não aparece.

### RF-05 — Receita em destaque

- **Given** receitas publicadas
  **When** a home abre
  **Then** a receita publicada mais recente aparece num cartão grande, com a capa, o rótulo
  "A receita mais nova", o título como `h2` com o link para a receita, o resumo e a linha com
  categoria, tempo de preparo e porções.
- **Given** o cartão em destaque
  **When** é percorrido por teclado ou leitor de tela
  **Then** tem um único link, o do título; a capa fica fora do Tab e do leitor de tela (spec
  008, RF-02).
- **Given** a receita mais recente sem capa
  **When** a home abre
  **Then** o cartão mostra o fundo reservado no lugar da foto, na mesma proporção.

### Categorias

### RF-06 — Entrada por categoria, com a contagem

- **Given** categorias com receita publicada
  **When** a home abre
  **Then** depois da abertura há a seção com o rótulo "Por categoria" e o `h2` "Comece pelo
  que tem vontade", com um link em forma de pílula por categoria: "Nome · N receitas" ("· 1
  receita" no singular), em ordem decrescente de receitas publicadas e, no empate, pelo nome.
- **Given** um link de categoria
  **When** o visitante o ativa
  **Then** a listagem abre filtrada por aquela categoria (spec 003, `?categoria=<slug>`).
- **Given** uma categoria sem receita publicada
  **When** a home abre
  **Then** ela não aparece; sem nenhuma categoria com receita publicada, a seção não
  aparece.

### Receitas recentes

### RF-07 — As recentes depois do destaque

**Substitui** spec 002, RF-06, primeiro cenário.

- **Given** mais de uma receita publicada
  **When** a home abre
  **Then** a seção com o rótulo "Recém-saídas do forno" e o `h2` "Receitas recentes" mostra
  até 3 receitas publicadas, as seguintes ao destaque, mais recentes primeiro, no cartão de
  sempre (`includes/cartao_receita.html`), e termina no botão "Ver todas as N receitas", com
  N igual ao total de receitas publicadas, levando à listagem.
- **Given** só uma receita publicada
  **When** a home abre
  **Then** a seção não aparece: a receita já está no destaque.
- **Given** nenhuma receita publicada
  **When** a home abre
  **Then** a seção mostra o estado vazio "Nenhuma receita publicada ainda." (spec 002, RF-06,
  segundo cenário, mantido).

### RF-08 — Cartões da mesma altura

- **Given** cartões de receita lado a lado, na home ou na listagem, com títulos de uma e de
  duas linhas
  **When** a página abre
  **Then** os cartões da mesma linha têm a mesma altura, e a linha de tempo e porções fica no
  pé de cada um, na mesma altura.

### Por dentro

### RF-09 — "Por dentro" aponta o código

- **Given** a home
  **When** o visitante chega depois das receitas
  **Then** a seção com o rótulo "Por dentro" e o `h2` "Como este blog foi feito" traz uma
  frase de abertura e quatro notas, cada uma com um `h3`, uma explicação curta e o caminho do
  arquivo como link para ele no repositório:
  - "Esta página": a view de função da home, `select_related` e `annotate(Count)`;
    `nucleo/views.py`.
  - "Busca e filtros": a `ListView` que filtra por texto, categoria e tag a partir da URL, com
    paginação; `receitas/views.py`.
  - "Segurança": a CSP nativa do Django, o limite de tentativas por IP e o honeypot;
    `blog_culinario/limitacao.py`.
  - "Specs antes do código": requisitos, design e tarefas aprovados antes do código; `specs/`.
- **Given** a seção
  **When** a página abre
  **Then** ela termina no botão "Ver o projeto no GitHub", que leva ao repositório.

### RF-10 — Notas fiéis ao código

- **Given** um caminho citado numa nota
  **When** a suíte roda
  **Then** o arquivo ou a pasta existe no repositório; renomear ou mover o arquivo sem
  atualizar a nota faz um teste falhar.
- **Given** a nota "Esta página"
  **When** se lê a view `home`
  **Then** ela usa o que a nota cita (`select_related` e `annotate(Count)`).

### Rótulos

### RF-11 — Rótulo em caixa alta acima do título

- **Given** as seções da home e a receita em destaque
  **When** a página abre
  **Then** um rótulo curto em caixa alta, fora do título, fica acima de cada `h2`: "Por
  categoria", "Recém-saídas do forno", "Por dentro" e, no destaque, "A receita mais nova".

### Rodapé

### RF-12 — Rodapé em colunas

- **Given** qualquer página que estende o `base.html`
  **When** a página abre
  **Then** o rodapé tem quatro colunas: a marca "Blog Culinário" com a frase "Receitas para
  todos os dias. Por dentro, um projeto Django open source."; "Navegar", com Início e
  Receitas, e Entrar e Cadastrar só para visitante não autenticado; "Categorias", com as
  categorias com receita publicada, na ordem do RF-06; e "O projeto", com "Código no
  GitHub", "Mapa da stack" (`docs/stack.md`), "Política de segurança" (`SECURITY.md`) e
  "Licença MIT" (`LICENSE`), cada um levando ao arquivo no repositório.
- **Given** cada coluna de links
  **When** é lida por leitor de tela
  **Then** é uma região de navegação com o nome do seu título.
- **Given** o rodapé
  **When** a página abre
  **Then** abaixo das colunas, separada por uma linha, fica "© <ano> Blog Culinário",
  centrado, no celular e no desktop.
- **Given** o rodapé até 720 px
  **When** a página abre
  **Then** a marca ocupa a largura toda e as três colunas de links ficam em duas colunas.

### RF-13 — Páginas de erro com o rodapé de sempre

- **Given** as páginas 400, 403, 403_csrf, 404 e 500
  **When** abrem
  **Then** continuam com o rodapé do `erro.html`, sem as categorias: não consultam o banco
  (spec 008, RF-04).

### Menu do celular

### RF-14 — Painel lateral abaixo da barra

- **Given** uma página até 720 px, com o menu fechado
  **When** o visitante ativa o botão do menu
  **Then** um painel entra pela direita, abaixo da barra do site, com 80% da largura e da
  barra até o fim da tela; a barra (marca e botão) continua visível e clicável, um véu
  escurece a página abaixo dela, e a página atrás do véu fica inerte (fora do Tab e do
  leitor de tela).
- **Given** um celular baixo, em que o conteúdo não cabe no painel
  **When** o menu abre
  **Then** o painel rola por dentro e nenhum link fica fora de alcance.
- **Given** uma página acima de 720 px
  **When** a página abre
  **Then** o menu é a barra de sempre, sem painel e sem véu.

### RF-15 — O botão vira X

- **Given** o menu fechado
  **When** a página abre
  **Then** o botão mostra o ícone de três linhas, com o nome "Abrir menu de navegação" e
  `aria-expanded="false"`, e tem pelo menos 48 x 48 px.
- **Given** o menu aberto
  **When** o visitante olha para o botão
  **Then** ele mostra um X, tem o nome "Fechar menu de navegação" e `aria-expanded="true"`.

### RF-16 — Links e o grupo "Sua conta"

- **Given** o menu aberto
  **When** o visitante lê o painel
  **Then** vêm primeiro os links Início e Receitas, cada um com pelo menos 48 px de altura e
  o da página atual marcado (`aria-current="page"`); logo abaixo, separado por uma linha, o
  grupo com o rótulo "Sua conta".
- **Given** um visitante não autenticado
  **When** o menu abre
  **Then** o grupo "Sua conta" tem os botões "Entrar" e "Cadastrar".
- **Given** um visitante autenticado
  **When** o menu abre
  **Then** o grupo "Sua conta" mostra "Olá, <nome de usuário>" e o botão "Sair", que encerra
  a sessão por POST, como hoje.

### RF-17 — Abrir e fechar

Mantém a spec 008, RF-06, e acrescenta o véu.

- **Given** o menu aberto pelo botão (clique, Enter ou Espaço)
  **When** ele abre
  **Then** o foco vai para o primeiro link do painel.
- **Given** o menu aberto
  **When** o visitante ativa o X ou aperta Esc
  **Then** o menu fecha e o foco volta ao botão.
- **Given** o menu aberto
  **When** o visitante toca no véu ou ativa um link do painel
  **Then** o menu fecha sem mover o foco para o botão.
- **Given** o painel abrindo ou fechando
  **When** o sistema pede movimento reduzido
  **Then** o painel aparece e some sem deslizar; sem esse pedido, desliza por `transform`.

## Requisitos não-funcionais

### RNF-01 — Sem dependência, campo ou migration novos

O redesenho não acrescenta pacote Python nem arquivo JavaScript de terceiros, não muda
nenhum modelo e não cria migration. O menu continua em `static/js/interacoes.js`, sem build.

### RNF-02 — Consultas fixas

O número de consultas da home não cresce com o número de receitas, categorias ou
comentários: a suíte o confere com `assertNumQueries` (ou equivalente) com poucas e com
muitas receitas. As categorias do rodapé custam uma consulta por página, a mesma em qualquer
página.

### RNF-03 — CSP, tokens e tema escuro

Nada inline nos templates (`<script>` sem `src`, `<style>`, `style=`, `on*=`): o
`nucleo/test_cabecalhos.py` continua passando. Toda cor nova sai de um token do
`tokens.css` com par no tema escuro; o véu do menu é o único token novo, e o texto sobre os
fundos novos passa de 4,5:1 nos dois temas (`nucleo/test_tema_escuro.py`).

### RNF-04 — Acessibilidade

A home tem um `h1` e títulos sem pulo de nível (`h1` → `h2` → `h3`), um link por cartão e
nenhum alvo de toque menor que 24 px. O axe-core não acusa violação na home nem no menu
aberto, a 390 e a 1280 px, nos dois temas. A conferência com leitor de tela do site inteiro
é feita à parte, fora desta spec.

### RNF-05 — Desempenho

A home continua no Lighthouse CI (mobile e desktop) dentro dos limites de
`.github/lighthouse/`. A capa do destaque é a maior imagem da primeira tela: carrega sem
`loading="lazy"` e com a proporção reservada, para não atrasar o LCP nem empurrar o texto.
As capas dos cartões continuam com `loading="lazy"`.

### RNF-06 — Catálogo em dia

O `docs/design-system.html` mostra os componentes novos: a pílula de categoria, o rótulo em
caixa alta, o cartão em destaque, a nota de código, o rodapé em colunas e o painel do menu
aberto.

## Perguntas em aberto / decisões resolvidas

**Perguntas em aberto:** nenhuma.

**Decisões resolvidas:**

1. **Abertura com a receita ao lado, no desktop** (decisão do mantenedor, 2026-11-17). A
   abertura centrada, só com texto, foi descartada: a foto de comida só aparecia depois das
   categorias. Com a receita ao lado, a primeira tela já mostra um prato, e a página fica mais
   curta.
2. **Celular com a abertura de hoje** (decisão do mantenedor, 2026-11-17). Título centrado e
   no tamanho atual; a receita vem logo abaixo da busca.
3. **Destaque é a receita mais nova, sem campo no Admin** (decisão de projeto, 2026-11-17). Um
   campo "destaque" exigiria migration e manutenção manual; a mais nova muda sozinha a cada
   publicação.
4. **Menu em painel lateral** (decisão do mantenedor, 2026-11-17). A cortina que desce na
   largura toda foi descartada: no painel lateral o X fica em cima do painel que ele fecha, e
   a barra continua à vista. "Entrar" e "Cadastrar" saem da lista de navegação porque são
   ações da conta, não lugares do site.
5. **"Mapa da stack" no rodapé, não "Specs"** (decisão do mantenedor, 2026-11-17). Para quem
   chega querendo conhecer o projeto, o `docs/stack.md` é a porta de entrada; as specs já têm
   o link na nota "Specs antes do código".
6. **Convite à conta em texto, não em botão** (decisão de projeto, 2026-11-17). A abertura
   fica com uma ação principal, a busca; criar conta só importa a quem quer comentar.
7. **"© ano" centrado** (decisão do mantenedor, 2026-11-17). O texto no centro marca o fim da
   página.

## Testes

### RF-18 — A suíte cobre o redesenho

- HTML da home: as duas colunas (classes) e o `h1`; o formulário de busca (método, `action`,
  nome do campo, rótulo); a linha de números com plural, singular e zero; o convite só para
  anônimo; o destaque com um link e a capa sem `loading="lazy"`; as categorias com contagem,
  ordem e link de filtro, sem a categoria vazia; as 3 recentes sem repetir o destaque; o
  botão "Ver todas as N receitas"; os estados com 0 e com 1 receita publicada.
- "Por dentro": os quatro `h3`, os links para o repositório e a existência de cada caminho
  citado (RF-10).
- Rótulos: o texto de cada um, fora do `h2`.
- Rodapé: as quatro colunas, as regiões de navegação com nome, Entrar e Cadastrar só para
  anônimo, as categorias, os quatro links do projeto e o "©" centrado; as páginas de erro sem
  as categorias.
- Menu: o botão com nome, `aria-expanded` e o X; os links com `aria-current`; o grupo "Sua
  conta" para anônimo e para autenticado; o `inert` e o véu no `interacoes.js`.
- CSS lido do arquivo: a mesma altura dos cartões, o `transform` do painel e o bloco de
  movimento reduzido.
- Consultas fixas na home (RNF-02), CSP sem nada inline e contraste dos tokens novos
  (RNF-03).

## Adendo (2026-11-17): página da receita e listagem

> Status do adendo: aprovado (2026-11-17). O texto acima é o aprovado em 2026-11-17 e fica como está; o
> adendo acrescenta requisitos, com a numeração continuando a dele.

**Contexto.** Depois do redesenho da home, a página da receita e a listagem ficaram com o
desenho de antes, e a diferença aparece logo no clique seguinte:

- **Receita.** Tudo fica numa coluna estreita à esquerda; no desktop, sobram cerca de 380 px
  vazios à direita, embaixo da capa larga. Tempo, porções, autor e data dividem uma linha cinza
  solta. Os passos são parágrafos com o número digitado no próprio texto, e a nota de fonte da
  receita tem o mesmo peso dos passos. Sem comentários, a seção termina na frase "Entre para
  deixar um comentário.", e a página acaba sem um próximo passo.
- **Listagem.** Não há filtro de categoria à vista: ele só existe pelos links da home, do
  rodapé e dos cartões. A busca tem o campo na largura toda e o rótulo cinza e pequeno, e
  destoa da busca da home.

O desenho foi validado num protótipo a 390 e 1280 px, com o HTML e o CSS do blog, antes deste
adendo.

**Objetivos do adendo.**

- Deixar a receita fácil de seguir enquanto se cozinha: ingredientes à vista ao lado dos
  passos no desktop e passos numerados em qualquer largura.
- Dar à receita uma saída: outras receitas para continuar navegando.
- Pôr o filtro de categoria na listagem, com a contagem, no mesmo desenho das pílulas da home.
- Dar à busca da listagem o desenho da busca da home.

**Não-objetivos do adendo.**

- **Modelo e Admin:** nenhum campo novo e nenhuma migration. Os passos continuam no campo de
  texto `modo_de_preparo`, como são escritos hoje.
- **Entrar, Cadastro e páginas de erro:** ficam como estão.
- **Paginação:** continua com 9 receitas por página (spec 002, RF-02, e spec 003, RF-06).
- **Formulário de comentário e lista de comentários com conteúdo:** ficam como estão (spec 005
  e spec 007).
- **"Mais receitas" por popularidade ou avaliação:** o blog não conta visitas nem avaliações;
  a seção usa só a categoria e a data.
- **Paleta, fontes e tokens existentes:** não mudam.

**Personas do adendo.**

- Como **quem cozinha com o celular ou o notebook na bancada**, quero ver os ingredientes
  enquanto leio os passos e saber em que passo estou pelo número.
- Como **visitante que terminou de ler uma receita**, quero uma sugestão do que cozinhar
  depois, de preferência do mesmo tipo.
- Como **visitante na listagem**, quero filtrar por categoria sem voltar à home e saber
  quantas receitas há em cada uma.
- Como **visitante de teclado ou leitor de tela**, quero os títulos em ordem, os passos
  anunciados como lista numerada e o filtro ativo anunciado.

### Página da receita

### RF-19 — Ficha de tempo e rendimento, autoria abaixo

- **Given** uma receita publicada
  **When** a página abre
  **Then** abaixo do resumo há uma ficha com dois itens, cada um com o rótulo em caixa alta
  e o valor: "Preparo" com o tempo ("60 min") e "Rende" com as porções ("10 porções", "1
  porção" no singular).
- **Given** a ficha
  **When** é lida por leitor de tela
  **Then** é uma lista de definições: cada rótulo anunciado junto do seu valor.
- **Given** a ficha
  **When** a página abre
  **Then** logo abaixo dela, numa linha menor, vêm o autor e a data: "Por <autor> · publicado
  <tempo relativo>", com "Autor removido" no lugar do nome quando a receita não tem autor
  (spec 002, RF-03); as etiquetas das tags continuam abaixo dessa linha.

### RF-20 — Ingredientes num cartão

- **Given** uma receita publicada
  **When** a página abre
  **Then** os ingredientes ficam num cartão branco com o `h2` "Ingredientes" e um item por
  linha não vazia do campo `ingredientes`, separados por uma linha fina, sem marcador.

### RF-21 — Duas colunas no desktop

- **Given** a página da receita acima de 900 px
  **When** a página abre
  **Then** abaixo da ficha e das etiquetas há duas colunas: à esquerda, o cartão de
  ingredientes (RF-20); à direita, o modo de preparo (RF-22).
- **Given** as duas colunas e o visitante rolando a página pelos passos
  **When** o modo de preparo passa
  **Then** o cartão de ingredientes acompanha a rolagem e continua à vista até o fim dos
  passos.
- **Given** um cartão de ingredientes mais alto que a tela
  **When** o visitante rola a página
  **Then** nenhum ingrediente fica fora de alcance: o cartão rola por dentro.
- **Given** a página da receita até 900 px
  **When** a página abre
  **Then** há uma coluna, com o cartão de ingredientes antes do modo de preparo.

### RF-22 — Passos numerados

- **Given** um modo de preparo com parágrafos (blocos separados por linha em branco) que
  começam por um número seguido de ponto ou parêntese ("1." ou "1)")
  **When** a página abre
  **Then** esses parágrafos formam uma lista numerada (`<ol>`), um passo por item, com o
  número em destaque ao lado e sem o número digitado no texto.
- **Given** parágrafos que não começam por número
  **When** a página abre
  **Then** ficam como parágrafos, na posição em que estão; o que vem depois do último passo
  aparece em texto menor, separado dos passos por uma linha (a nota de fonte das receitas da
  demonstração, por exemplo).
- **Given** um modo de preparo sem nenhum parágrafo numerado
  **When** a página abre
  **Then** aparece como hoje: parágrafos, sem lista.
- **Given** o banco
  **When** a página é exibida
  **Then** o texto gravado em `modo_de_preparo` não muda: o número sai só na exibição.

### RF-23 — Convite a comentar num cartão

- **Given** um visitante não autenticado numa receita sem comentários
  **When** a página abre
  **Then** a seção "Comentários" mostra um cartão com "Ainda não há comentários. Seja o
  primeiro a comentar!" e o botão "Entrar para comentar", que leva ao login e volta para a
  receita depois de entrar.
- **Given** um visitante não autenticado numa receita com comentários
  **When** a página abre
  **Then** depois da lista de comentários vem o mesmo cartão, com "Entre para deixar um
  comentário." e o botão "Entrar para comentar".
- **Given** um visitante autenticado
  **When** a página abre
  **Then** a seção fica como hoje: a frase de estado vazio, quando não há comentários, e o
  formulário de comentário.

### RF-24 — Mais receitas

- **Given** outras receitas publicadas além da que está aberta
  **When** a página abre
  **Then** depois dos comentários há a seção com o rótulo "Continue cozinhando" e o `h2`
  "Mais receitas", com até 3 receitas publicadas no cartão de sempre
  (`includes/cartao_receita.html`): primeiro as da mesma categoria, mais recentes primeiro, e,
  se faltarem, as mais recentes das outras categorias.
- **Given** a seção
  **When** a página abre
  **Then** a receita aberta não aparece nela, e nenhuma receita aparece duas vezes.
- **Given** nenhuma outra receita publicada
  **When** a página abre
  **Then** a seção não aparece.

### Listagem

### RF-25 — Busca com o desenho da home

- **Given** a listagem
  **When** a página abre
  **Then** a busca tem o desenho da busca da home (RF-02): o rótulo visível "Buscar por
  título ou ingrediente" acima do campo, o campo `q` arredondado com o exemplo "Ex.: cenoura"
  e o botão "Buscar" ao lado, alinhados à esquerda, com a largura do campo limitada no
  desktop.
- **Given** a listagem filtrada por categoria ou tag
  **When** o visitante busca um termo
  **Then** o filtro ativo continua aplicado (spec 003, RF-07).

### RF-26 — Pílulas de categoria na listagem

- **Given** categorias com receita publicada
  **When** a listagem abre
  **Then** entre a busca e a grade há uma região de navegação com o nome "Categorias" e uma
  pílula por categoria, no desenho e na ordem da home (RF-06): "Nome · N", com N o número de
  receitas publicadas da categoria; antes delas, a pílula "Todas · N", com N o total de
  receitas publicadas.
- **Given** a listagem filtrada por uma categoria
  **When** a página abre
  **Then** a pílula daquela categoria fica preenchida e marcada com `aria-current="page"`;
  sem filtro de categoria, a marcada é "Todas".
- **Given** uma busca ou uma tag ativa
  **When** o visitante ativa uma pílula
  **Then** a listagem abre na primeira página, filtrada pela categoria escolhida (ou sem
  categoria, em "Todas"), mantendo a busca e a tag.
- **Given** as contagens das pílulas
  **When** há uma busca ou uma tag ativa
  **Then** os números continuam sendo os de receitas publicadas por categoria, sem considerar
  a busca nem a tag.
- **Given** nenhuma categoria com receita publicada
  **When** a listagem abre
  **Then** as pílulas não aparecem.

### RF-27 — A paginação continua com 9 por página

- **Given** mais de 9 receitas no resultado
  **When** a listagem abre
  **Then** a paginação é a de hoje: 9 receitas por página, preservando a busca e os filtros
  (spec 002, RF-02, e spec 003, RF-06).

### RNF-07 — Sem dependência, campo ou migration novos

O adendo não acrescenta pacote Python nem JavaScript, não muda nenhum modelo e não cria
migration. A seção "Mais receitas" e as contagens das pílulas saem de consultas.

### RNF-08 — Consultas fixas

O número de consultas da página da receita e da listagem não cresce com o número de
receitas, categorias, tags ou comentários: a suíte o confere com `assertNumQueries` (ou
equivalente) com poucas e com muitas receitas. "Mais receitas" custa no máximo duas
consultas; as pílulas, uma.

### RNF-09 — CSP, tokens e tema escuro

Nada inline nos templates (`nucleo/test_cabecalhos.py`). Toda cor sai de um token do
`tokens.css` com par no tema escuro, e o texto sobre os fundos novos (pílula marcada, número
do passo, cartões) passa de 4,5:1 nos dois temas (`nucleo/test_tema_escuro.py`).

### RNF-10 — Acessibilidade

A receita tem um `h1` e, em ordem, os `h2` "Ingredientes", "Modo de preparo", "Comentários"
e "Mais receitas", com os cartões em `h3`; os passos são uma lista ordenada. Na listagem, a
região "Categorias" e a pílula marcada são anunciadas. Nenhum alvo de toque menor que 24 px,
e o axe-core não acusa violação nas duas páginas, a 390 e a 1280 px, nos dois temas.

### RNF-11 — Desempenho

A listagem e a receita continuam no Lighthouse CI (mobile e desktop) dentro dos limites de
`.github/lighthouse/`. As capas de "Mais receitas" carregam com `loading="lazy"`.

### RNF-12 — Catálogo em dia

O `docs/design-system.html` mostra os componentes novos: a ficha, o cartão de ingredientes,
os passos numerados, o cartão de convite a comentar e a pílula marcada.

**Perguntas em aberto do adendo:** nenhuma.

**Decisões resolvidas do adendo:**

1. **Receita em duas colunas no desktop** (decisão do mantenedor, 2026-11-17). A coluna única
   no centro foi descartada: a lista de ingredientes sai da tela quando se chega aos passos.
2. **Pílulas acima da grade na listagem** (decisão do mantenedor, 2026-11-17). A coluna
   lateral de categorias foi descartada: a grade cairia para 2 colunas, e o celular e o
   desktop ficariam diferentes.
3. **"Mais receitas" entra** (decisão do mantenedor, 2026-11-17), pela categoria e pela data.
   Não reabre o não-objetivo "mais populares" da spec, que pedia contagem de visitas.
4. **Paginação continua em 9** (decisão do mantenedor, 2026-11-17): três linhas completas de
   três cartões no desktop.
5. **Passos numerados sem migration** (decisão de projeto, 2026-11-17). O número digitado sai
   só na exibição; um campo por passo exigiria migration e mudaria o Admin. A receita sem
   número continua como hoje.
6. **A pílula mantém a busca e a tag** (decisão de projeto, 2026-11-17), como a busca já
   mantém a categoria e a tag (spec 003, RF-04 e RF-07).
7. **Ficha sem a categoria** (decisão de projeto, 2026-11-17). A categoria já aparece no
   rótulo acima do título; repeti-la na ficha a quebrava em duas linhas no celular.

### RF-28 — A suíte cobre o adendo

- Receita: a ficha (`<dl>`, rótulos, singular e plural); a linha de autoria, com "Autor
  removido"; o cartão de ingredientes com um item por linha não vazia; as duas colunas e o
  cartão fixo ao rolar (CSS lido do arquivo); os passos numerados com o número tirado, os
  parágrafos sem número no lugar e o caso sem nenhum passo numerado; o texto do banco intacto.
- Comentários: o cartão com o botão para anônimo, com e sem comentários, e o link de login
  que volta para a receita; a seção de hoje para autenticado.
- "Mais receitas": a mesma categoria primeiro, o complemento com as outras, a receita aberta
  fora, sem repetição, o limite de 3, a seção ausente sem outras receitas e as capas com
  `loading="lazy"`.
- Listagem: a busca com o desenho da home e os filtros ocultos; as pílulas na ordem, com
  "Todas", as contagens que ignoram a busca, a marcada com `aria-current`, os links que
  mantêm a busca e a tag e voltam à primeira página, e a ausência sem categorias; a paginação
  com 9.
- Consultas fixas nas duas páginas (RNF-08), CSP sem nada inline e contraste dos fundos novos
  (RNF-09).
