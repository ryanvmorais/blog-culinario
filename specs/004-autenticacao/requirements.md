---
feature: Autenticação de usuários (cadastro, login, logout)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 004 — Autenticação de usuários (cadastro, login, logout)

## Contexto e problema

O app `usuarios` existe só como esqueleto desde a fundação do projeto — o
site inteiro hoje é anônimo, sem nenhuma forma de criar conta ou entrar.
Esta spec implementa a autenticação nativa do Django
(`django.contrib.auth`, por decisão já registrada em `docs/stack.md`: sem
lib externa, por transparência didática) e é pré-requisito direto da
próxima spec (comentários em receitas, que exige usuário autenticado).

## Objetivos

- Cadastro de novo usuário (username, email opcional, senha com
  confirmação).
- Login e logout usando as views prontas do `django.contrib.auth`.
- Navbar reflete o estado de autenticação (link de entrar vs. saudação +
  sair).
- Redirecionamento pós-login para a página de origem (`?next=`), para
  sustentar o fluxo "tentou comentar sem estar logado" da próxima spec.
- Feedback visual de sucesso/erro (mensagens do `django.contrib.messages`,
  já instalado mas ainda não usado em nenhum template).

## Não-objetivos

- Recuperação de senha por email — exigiria um backend de email real; o
  projeto só tem o console backend (`settings/base.py`). Fica para uma
  spec futura se/quando houver infraestrutura de email.
- Verificação de email/confirmação de conta.
- Login social (Google, GitHub, etc.).
- Página de perfil com edição de dados, avatar ou bio.
- Grupos/permissões além do `is_staff`/`is_superuser` que o admin já usa.
- Proteção anti-bot no formulário (captcha, honeypot, rate limiting) — a
  auditoria de segurança prevista no roadmap do projeto é o momento certo
  para revisar isso de forma abrangente, não esta spec isoladamente.

## Personas

- Como **visitante**, quero criar uma conta para poder comentar nas
  receitas (funcionalidade da próxima spec).
- Como **usuário cadastrado**, quero entrar e sair da minha conta, e ver
  claramente na navbar se estou autenticado.

## Requisitos funcionais

### RF-01 — Cadastro de novo usuário

- **Given** um visitante acessa a página de cadastro
  **When** preenche `username`, senha e confirmação de senha válidas (email
  é opcional)
  **Then** uma conta é criada, o visitante é automaticamente autenticado, e
  é redirecionado para a home com uma mensagem de boas-vindas.
- **Given** o `username` escolhido já existe
  **When** o formulário é submetido
  **Then** exibe um erro claro nesse campo, sem criar a conta.
- **Given** a senha não atende aos validadores já configurados em
  `AUTH_PASSWORD_VALIDATORS` (settings/base.py, spec de fundação)
  **When** o formulário é submetido
  **Then** exibe a mensagem de validação correspondente (ex.: "senha
  parecida demais com o nome de usuário", "senha comum demais").
- **Given** as duas senhas informadas não coincidem
  **When** o formulário é submetido
  **Then** exibe um erro claro, sem criar a conta.

### RF-02 — Login

- **Given** um usuário com conta existente acessa a página de login
  **When** submete `username` e senha corretos
  **Then** é autenticado e redirecionado para `?next=` (se veio de uma
  página que exigia login) ou para a home, com mensagem de boas-vindas.
- **Given** credenciais incorretas (usuário inexistente ou senha errada)
  **When** o formulário é submetido
  **Then** exibe uma mensagem de erro genérica ("nome de usuário ou senha
  incorretos"), sem indicar qual dos dois campos está errado — evita
  confirmar para um atacante se um username existe.

### RF-03 — Logout

- **Given** um usuário autenticado
  **When** aciona "Sair" na navbar
  **Then** a sessão é encerrada e é redirecionado para a home com uma
  mensagem de despedida.

### RF-04 — Navbar reflete o estado de autenticação

- **Given** um visitante anônimo
  **When** qualquer página carrega
  **Then** a navbar mostra um link "Entrar" (e, junto, um link para
  cadastro).
- **Given** um usuário autenticado
  **When** qualquer página carrega
  **Then** a navbar mostra o `username` e um botão/link "Sair" no lugar de
  "Entrar".

### RF-05 — Redirecionamento pós-login preserva o destino original

- **Given** uma rota futura exige login (`@login_required`, spec de
  comentários) e um visitante anônimo tenta acessá-la
  **When** é redirecionado para o login e depois autentica com sucesso
  **Then** volta exatamente para a página que tentou acessar, não para a
  home — via parâmetro `next` (comportamento padrão do
  `LoginRequiredMixin`/`login_required` combinado com `LoginView`).

### RF-06 — Mensagens de feedback

- **Given** uma ação de cadastro, login ou logout é concluída
  **When** a próxima página renderiza
  **Then** exibe uma mensagem correspondente (sucesso ou erro) usando
  `django.contrib.messages`, num local visível do layout (`base.html`).

## Requisitos não-funcionais

### RNF-01 — Reaproveitar as views nativas do Django

Login e logout usam `django.contrib.auth.views.LoginView`/`LogoutView`
diretamente (só com `template_name` customizado) — nenhuma reimplementação
de autenticação de sessão, hashing de senha ou CSRF.

### RNF-02 — Senha nunca em texto plano em lugar nenhum

Nenhum log, mensagem de erro ou template exibe a senha submetida — só os
erros de validação já produzidos pelos formulários nativos do Django.

## Perguntas em aberto

Nenhuma — os pontos que poderiam gerar ambiguidade (recuperação de senha,
verificação de email, proteção anti-bot) já foram resolvidos em
"Não-objetivos", com a justificativa de cada adiamento.

## Testes

- **RF-01:** cadastro com dados válidos cria o usuário e autentica
  automaticamente; username duplicado, senha fraca e senhas divergentes
  cada um gera erro sem criar a conta.
- **RF-02:** login com credenciais corretas autentica; credenciais erradas
  mostram mensagem genérica (não indicam qual campo errou).
- **RF-03:** logout encerra a sessão (requisição autenticada após logout
  deixa de ter `request.user.is_authenticated`).
- **RF-04:** HTML da navbar contém "Entrar" para cliente anônimo e o
  `username` + "Sair" para cliente autenticado.
- **RF-05:** acessar uma rota `@login_required` anônimo redireciona para
  login com `?next=`; logar em seguida redireciona de volta a essa rota.
- **RF-06:** resposta pós-cadastro/login/logout contém a mensagem
  esperada no HTML.
