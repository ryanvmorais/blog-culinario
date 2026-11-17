---
feature: Comentários em receitas
status: concluído
date: 2026-09-12
related:
  - 001-modelagem-receitas/requirements.md
  - 002-listagem-detalhe-receitas/requirements.md
  - 004-autenticacao/requirements.md
origin: concepcao
---

# 005 — Comentários em receitas

## Contexto e problema

A modelagem original (spec 001) já previa um model `Comentario` na visão
geral do domínio, mas ele nunca foi criado — ficou para depois de existir
autenticação (spec 004), que é pré-requisito direto: só faz sentido
comentar como usuário identificado. Esta spec fecha esse ciclo: modelo,
formulário na página de detalhe, exigência de login, e moderação básica no
admin.

## Objetivos

- Modelo `Comentario` vinculado a uma `Receita` e a um autor autenticado.
- Formulário de novo comentário na página de detalhe, visível só para
  quem está logado (visitante anônimo vê um convite para entrar).
- Envio de comentário exige autenticação — reusa o `LOGIN_URL`/`?next=`
  já preparados pela spec 004, agora com uma rota `@login_required` real.
- Moderação básica no admin: listar, e aprovar/reprovar sem precisar
  apagar.

## Não-objetivos

- Respostas aninhadas (threading/replies a um comentário).
- Edição ou exclusão de comentário pelo próprio autor.
- Curtidas/reações em comentário.
- Notificação por email de novo comentário — depende da infraestrutura
  de email real que ainda não existe (ver `docs/stack.md` e a decisão
  registrada de que isso é "adiado até ter infra", não descartado).
- Proteção anti-spam além de exigir login (rate limiting, captcha) — fica
  para a auditoria de segurança do roadmap do projeto.
- Paginação de comentários — assume-se volume pequeno por receita neste
  momento; pode virar uma melhoria futura se necessário.

## Personas

- Como **leitor autenticado**, quero deixar um comentário numa receita que
  eu testei, para compartilhar minha experiência.
- Como **visitante anônimo**, ao tentar comentar quero ser levado ao login
  e, depois de entrar, voltar direto pra receita — não para a home.
- Como **administrador**, quero poder esconder um comentário inadequado
  sem precisar apagá-lo permanentemente.

## Requisitos funcionais

### RF-01 — Modelo Comentario

- **Given** um usuário autenticado envia um comentário válido numa receita
  **When** o formulário é submetido
  **Then** um `Comentario` é criado com `receita`, `autor` (o usuário
  logado), `texto`, `criado_em` (automático) e `aprovado=True` por
  padrão.
- **Given** uma `Receita` é excluída
  **When** a exclusão é confirmada
  **Then** todos os comentários associados são excluídos junto
  (`on_delete=CASCADE`) — comentário não sobrevive sem a receita que
  comenta.
- **Given** o autor de um comentário é excluído da base
  **When** a exclusão do usuário é confirmada
  **Then** o comentário permanece com `autor=NULL`
  (`on_delete=SET_NULL`, `null=True`) — mesma política já usada em
  `Receita.autor` (spec 001, ADR-2), pelo mesmo motivo: preservar o
  conteúdo mesmo sem o autor.

### RF-02 — Exibição de comentários na página de detalhe

- **Given** uma receita tem comentários aprovados
  **When** a página de detalhe carrega
  **Then** exibe a lista de comentários abaixo do conteúdo da receita,
  ordenados do mais antigo para o mais novo, cada um com autor, data e
  texto.
- **Given** um comentário está com `aprovado=False`
  **When** a página de detalhe carrega (para qualquer visitante, incluindo
  o autor do comentário)
  **Then** esse comentário não aparece na lista pública.
- **Given** um comentário cujo autor foi removido (`autor=NULL`)
  **When** a página de detalhe renderiza esse comentário
  **Then** exibe "Usuário removido" no lugar do nome, sem quebrar a
  página (mesmo tratamento já usado para `Receita.autor`, spec 002 RF-03).

### RF-03 — Formulário visível só para quem está logado

- **Given** um visitante autenticado acessa a página de detalhe
  **When** a página carrega
  **Then** exibe um formulário de novo comentário (campo de texto +
  botão de enviar).
- **Given** um visitante anônimo acessa a página de detalhe
  **When** a página carrega
  **Then** exibe, no lugar do formulário, um convite para entrar (link
  para `usuarios:entrar` com `?next=` apontando de volta pra essa mesma
  receita).

### RF-04 — Envio de comentário

- **Given** um usuário autenticado preenche o campo de texto com conteúdo
  válido
  **When** submete o formulário
  **Then** o comentário é criado e o usuário é redirecionado de volta
  para a página de detalhe da receita, com uma mensagem de sucesso, e o
  novo comentário aparece na lista.

### RF-05 — Validação de conteúdo

- **Given** o campo de texto está vazio ou contém só espaços em branco
  **When** o formulário é submetido
  **Then** o comentário não é criado e a página reexibe o formulário com
  um erro de validação claro.

### RF-06 — Comentar exige login (integra com a spec 004)

- **Given** um visitante anônimo tenta submeter o formulário de comentário
  diretamente (ex.: reenviando uma requisição, ou a rota é acessada sem
  sessão)
  **When** a requisição chega à view de criação de comentário
  **Then** é redirecionado para `usuarios:entrar` com `?next=` apontando
  de volta para a página da receita — ao autenticar com sucesso, volta
  exatamente para lá (fluxo ponta a ponta que a spec 004 preparou, agora
  testado com uma rota `@login_required` real).

### RF-07 — Moderação básica no admin

- **Given** o admin acessa a listagem de comentários em `/admin/`
  **When** a página carrega
  **Then** exibe texto (truncado), receita, autor, `aprovado` e
  `criado_em` como colunas, com filtro por `aprovado` e busca por texto.
- **Given** o admin quer esconder um comentário sem apagá-lo
  **When** desmarca `aprovado` (edição em linha na listagem ou no
  formulário do comentário) e salva
  **Then** o comentário deixa de aparecer na página pública (RF-02), mas
  continua no banco.

## Requisitos não-funcionais

### RNF-01 — Sem N+1 na lista de comentários

A queryset de comentários da página de detalhe usa `select_related("autor")`
— a lista de uma receita não pode disparar uma query de autor por
comentário.

### RNF-02 — Reaproveitar a infraestrutura de login existente

A view de criação de comentário usa `LoginRequiredMixin` (ou o decorator
`@login_required`) — nenhuma lógica de autenticação nova, só a que a spec
004 já forneceu.

## Perguntas em aberto

Nenhuma — moderação por flag (`aprovado`, visível/oculto) em vez de fila de
aprovação prévia foi decidida acima (RF-01: comentário nasce `aprovado=True`)
para manter o fluxo simples num blog de baixo volume com autores sempre
autenticados; a alternativa de pré-moderação obrigatória fica registrada
como ADR na fase de design, caso valha revisitar depois.

## Testes

- **RF-01:** criar comentário válido gera os campos esperados; excluir a
  receita apaga os comentários; excluir o autor preserva o comentário com
  `autor=None`.
- **RF-02:** comentário aprovado aparece na página, ordenado do mais
  antigo ao mais novo; comentário reprovado não aparece; comentário sem
  autor renderiza "Usuário removido".
- **RF-03:** HTML da página de detalhe contém o formulário para cliente
  autenticado e o convite de login (com `?next=`) para cliente anônimo.
- **RF-04/RF-05:** POST válido autenticado cria o comentário e redireciona
  com mensagem de sucesso; POST com texto vazio/só espaço não cria nada e
  reexibe o erro.
- **RF-06:** POST anônimo na rota de criação de comentário redireciona
  para login com `?next=` correto; logar em seguida volta para a receita.
- **RF-07:** admin vê a listagem com os filtros esperados; desmarcar
  `aprovado` remove o comentário da página pública (teste de integração
  entre admin e a view pública).

## Adendo (2026-11-16): tamanho máximo do comentário

> Status do adendo: concluído (2026-11-16). O texto acima é o aprovado em 2026-09-12 e fica como
> está; o adendo acrescenta requisitos, com a numeração continuando a dele.

**Contexto.** O `texto` do comentário é um `TextField` sem limite, e o formulário
aceita o que o Django deixar passar num pedido (2,5 MB, o `DATA_UPLOAD_MAX_MEMORY_SIZE`
padrão). A auditoria de segurança de 2026-11-16 apontou o risco (CWE-770, baixo): um
usuário logado pode publicar um bloco de texto enorme, que é guardado e exibido inteiro
na página da receita. No modo demonstração nada é gravado, mas quem clona o projeto
herda o formulário sem teto.

**Objetivos do adendo.**

- Limitar o comentário a 2.000 caracteres, no formulário e no navegador.
- Dizer ao visitante por que o comentário longo foi recusado, com uma mensagem própria,
  diferente da do comentário vazio.

**Não-objetivos do adendo.**

- Contador de caracteres na tela (exigiria JavaScript novo).
- Mudar a coluna do banco: o limite vale no formulário, como as outras regras de
  conteúdo do RF-05.
- Rever os comentários que já existem.

### RF-08 — Comentário com até 2.000 caracteres

- **Given** um usuário logado na página de uma receita
  **When** o formulário de comentário é exibido
  **Then** o campo de texto não aceita digitar mais de 2.000 caracteres
  (`maxlength="2000"`).
- **Given** um comentário com 2.000 caracteres ou menos (depois de tirar os espaços das
  pontas)
  **When** o formulário é enviado
  **Then** o comentário é aceito, como hoje.
- **Given** um comentário com mais de 2.000 caracteres (um envio que não passou pelo
  campo do navegador)
  **When** o formulário é enviado
  **Then** o comentário não é criado, e a página da receita volta com a mensagem "O
  comentário pode ter até 2.000 caracteres.".
- **Given** um comentário vazio ou só com espaços
  **When** o formulário é enviado
  **Then** a mensagem continua a do RF-05, "O comentário não pode ficar vazio.".
- **Given** o modo demonstração ligado (spec 009)
  **When** chega um comentário longo demais
  **Then** vale a mesma recusa, com a mesma mensagem.

### RNF-03 — Sem migration

O limite fica no formulário (`FormularioComentario`), sem mudar o modelo: nenhuma
migration nova, e os comentários gravados continuam válidos.

**Decisões resolvidas do adendo.**

1. **2.000 caracteres** (2026-11-16). Cerca de 300 palavras: sobra para uma dúvida ou
   uma adaptação da receita, e corta o envio de megabytes.
2. **O texto longo também se perde na recusa** (2026-11-16). O ADR-3 do design (erro por
   mensagem, sem reexibir o formulário) continua: com o `maxlength` no campo, só um envio
   feito fora do navegador chega acima do limite.

### RF-09 — A suíte cobre o adendo

- O campo do formulário sai com `maxlength="2000"` no HTML da receita.
- 2.000 caracteres são aceitos; 2.001 não criam o comentário e mostram a mensagem do
  RF-08, com o modo demonstração ligado e desligado.
- O comentário vazio continua com a mensagem do RF-05.
