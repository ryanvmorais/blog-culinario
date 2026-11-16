---
feature: Modo demonstração
status: concluído
date: 2026-11-16
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
  - 006-limitacao-de-taxa/requirements.md
  - 007-honeypot-e-time-trap/requirements.md
origin: concepcao
---

# 009 — Modo demonstração

## Contexto e problema

O blog funciona como demonstração pública de um projeto educacional. Hoje,
qualquer visitante cria uma conta (o `CadastroView` grava o usuário e já autentica,
spec 004) e qualquer usuário autenticado publica um comentário que aparece na hora:
o `Comentario.aprovado` nasce `True` e a moderação é reativa, pelo admin (spec 005).

Numa demo sem ninguém moderando, isso traz dois problemas:

- **Comentário sem moderação:** spam e conteúdo ofensivo aparecem na página assim que
  são enviados. O honeypot, o time-trap (spec 007) e o limite de taxa (spec 006) freiam
  bots, não uma pessoa.
- **Conta guarda dado pessoal:** o cadastro pede e-mail (opcional) e grava nome de usuário
  e senha de estranhos, o que faz do site um controlador de dados pessoais (LGPD) sem
  nenhuma necessidade, já que o objetivo é ensinar.

Quem quiser ver o cadastro e o comentário gravando de verdade tem o código: clona o
repositório e roda localmente.

## Objetivos

- Um interruptor de ambiente, `MODO_DEMONSTRACAO`, desligado por padrão, que a instância
  pública liga.
- Com o modo ligado, cadastro e comentário continuam validando como hoje, mas não gravam
  nada e respondem com um aviso educativo que aponta o repositório.
- O visitante é avisado **antes** de preencher (aviso fixo acima do formulário), não só
  depois de enviar.
- O login continua funcionando, com uma conta de demonstração pública cujas credenciais
  aparecem na tela de login, para o visitante ver a experiência logada e o formulário
  de comentário.
- Com o modo desligado, o site se comporta exatamente como hoje.

## Não-objetivos

- Envio de e-mail (recuperação de senha, notificações): a demo não envia nem recebe
  e-mail; o backend de console segue como está.
- Mudar o limite de taxa do login ou do comentário (spec 006), o honeypot e o time-trap
  (spec 007).
- Desligar o Admin: a conta de demonstração não é staff, e o Admin segue protegido
  pelo login normal. O caminho passou a ser configurável pelo `ADMIN_URL` na spec 011
  (RF-14, 2026-11-16), sem mudar o que esta spec entrega.
- Apagar ou bloquear comentários e contas que já existem no banco.
- Hospedagem, domínio e descoberta (`robots.txt`, `sitemap.xml`): ficam para specs
  próprias.

## Personas

- Como **visitante da demo**, quero saber antes de preencher que nada será gravado, para
  não perder tempo, e ainda assim ver como o cadastro valida e como é o site logado.
- Como **aprendiz de Django**, quero ver no código como um interruptor de ambiente muda o
  comportamento de uma view sem duplicar a lógica de validação.
- Como **quem clona o projeto**, quero rodar tudo localmente com cadastro e comentário
  funcionando de verdade, sem configurar nada.

## Requisitos funcionais

### RF-01 — Interruptor `MODO_DEMONSTRACAO`

- **Given** a variável de ambiente `MODO_DEMONSTRACAO` ausente
  **When** o site sobe (em desenvolvimento ou em produção)
  **Then** o modo fica desligado e cadastro, login e comentário se comportam como hoje,
  sem nenhum aviso de demonstração nem credencial na tela.
- **Given** `MODO_DEMONSTRACAO=True`
  **When** o site sobe
  **Then** o modo fica ligado e valem os RF-02 a RF-06.

### RF-02 — Cadastro: aviso antes de preencher

- **Given** o modo ligado
  **When** o visitante abre `/usuarios/cadastro/`
  **Then** entre o `h1` e o formulário aparece um aviso informativo: "**Cadastro de
  demonstração:** nenhuma conta é criada. Para ver o blog por dentro, entre com a conta
  de demonstração.", em que "entre com a conta de demonstração" é um link para o login.
- **Given** o modo desligado
  **When** o visitante abre o cadastro
  **Then** o aviso não aparece.

### RF-03 — Cadastro: valida e não grava

- **Given** o modo ligado
  **When** o visitante envia o cadastro com erro (senha curta, senhas diferentes, usuário
  que já existe)
  **Then** a página volta com os mesmos erros de campo de hoje.
- **Given** o modo ligado
  **When** o visitante envia um cadastro válido
  **Then** nenhum usuário é criado, a sessão continua anônima e a página mostra a
  mensagem informativa: "Este blog é um projeto educacional e não cria contas. Para ver
  como o cadastro funciona, clone ou baixe o código no GitHub. Para comentar, entre com
  a conta de demonstração.", em que "clone ou baixe o código no GitHub" é um link para o
  repositório.

### RF-04 — Login: credenciais da conta de demonstração

- **Given** o modo ligado
  **When** o visitante abre `/usuarios/entrar/`
  **Then** acima do formulário aparece um aviso informativo com o título "Conta de
  demonstração" e, como texto selecionável numa lista de definição, o usuário
  `visitante` e a senha `receitas-demo`.
- **Given** o modo ligado
  **When** o visitante entra com essas credenciais
  **Then** o login funciona como hoje (mensagem de boas-vindas, `?next=` respeitado) e o
  limite de tentativas da spec 006 continua valendo.
- **Given** o modo desligado
  **When** o visitante abre o login
  **Then** o aviso e as credenciais não aparecem.

### RF-05 — Conta de demonstração criada por comando

- **Given** um banco sem a conta `visitante`
  **When** quem opera o site roda `manage.py criar_conta_demonstracao`
  **Then** a conta é criada ativa, sem staff e sem superusuário, com a senha do RF-04.
- **Given** a conta `visitante` já existe com outra senha ou com staff ligado
  **When** o comando roda de novo
  **Then** a senha volta a ser a do RF-04, staff e superusuário ficam desligados e
  nenhuma conta duplicada é criada (comando idempotente).

### RF-06 — Comentário: aviso antes e nada publicado

- **Given** o modo ligado e um usuário autenticado na página de uma receita
  **When** a página carrega
  **Then** dentro do formulário, antes do campo de texto, aparece o aviso informativo:
  "**Comentários de demonstração:** nada é publicado."
- **Given** o modo ligado
  **When** o usuário envia um comentário válido
  **Then** nenhum comentário é gravado, a página volta para `#comentarios` e mostra a
  mensagem informativa: "Este blog é um projeto educacional e não publica comentários.
  Para ver como funciona, clone ou baixe o código no GitHub.", com o mesmo link do RF-03.
- **Given** o modo ligado
  **When** o envio cai no honeypot ou no time-trap (spec 007)
  **Then** a resposta é a mesma mensagem do envio válido, para o filtro continuar
  indistinguível de um sucesso (spec 007, ADR-3).
- **Given** o modo ligado
  **When** o envio está vazio ou o IP passou do limite (spec 006)
  **Then** a resposta é a mesma de hoje (erro de campo vazio ou de limite).
- **Given** o modo desligado
  **When** o usuário envia um comentário válido
  **Then** ele é publicado como hoje e o aviso não aparece.

## Requisitos não-funcionais

### RNF-01 — Sem dependência nova

O modo usa o que o projeto já tem: `django-environ` para ler a variável, o framework de
mensagens do Django e a classe `.mensagem--info` do `base.css`.

### RNF-02 — Validação num lugar só

O modo ligado não duplica regra de validação: o cadastro segue passando pelo
`FormularioCadastro` (e pelo `AUTH_PASSWORD_VALIDATORS`) e o comentário pelo
`FormularioComentario`; o modo só decide, depois de validar, se grava.

### RNF-03 — Avisos acessíveis e dentro do design system

Os avisos fixos usam `.mensagem--info` (cor só por token, nos dois temas) e o texto que
vem antes do formulário é lido pelo leitor de tela na ordem da página. O link da
mensagem pós-envio é um link de verdade (não texto escapado). As regras de interface da
spec 008 continuam valendo: mensagens da receita dentro de `#comentarios`, alinhamento à
esquerda na leitura.

### RNF-04 — Documentado para quem clona

`MODO_DEMONSTRACAO` aparece no `.env.example` com o padrão e o efeito, e o comando
`criar_conta_demonstracao` aparece nos comandos comuns.

## Decisões resolvidas

1. **Demo não grava cadastro nem comentário** (decisão de projeto, 2026-11-15): spam e
   conteúdo ofensivo apareceriam sem moderação, e contas guardariam dados pessoais de
   estranhos. Substitui a ideia de configurar envio de e-mail real.
2. **Aviso fixo antes do formulário**, não depois do botão (2026-11-16): lido antes do
   primeiro campo, então ninguém preenche à toa.
3. **Login continua real, com conta pública** (2026-11-15): sem ela o visitante nunca vê
   o formulário de comentário, que exige login. As credenciais (`visitante` /
   `receitas-demo`) são públicas de propósito; a conta não tem staff, e o modo impede que
   ela grave comentário.
4. **Conta criada por comando idempotente**, não por migration nem à mão no shell: a
   migration criaria a conta também em quem clona, e o comando pode ser repetido para
   corrigir uma senha trocada pelo Admin.
5. **`visitante` é diferente do `demo` do `semear_dados_demo`**: aquele é o autor fictício
   das receitas do Lighthouse CI, só com `DEBUG=True`; este é a conta pública da instância
   no ar.
6. **Honeypot no modo ligado responde a mensagem do modo**, não "Comentário publicado!":
   o falso sucesso precisa imitar o sucesso real daquele ambiente.

## Testes

### RF-07 — Suíte do modo demonstração

A suíte cobre, com `override_settings(MODO_DEMONSTRACAO=...)`:

- o padrão desligado quando a variável não existe (RF-01);
- cadastro: aviso presente só no modo ligado; envio inválido com os erros de hoje; envio
  válido sem criar usuário, sem autenticar e com a mensagem e o link (RF-02, RF-03);
- login: credenciais presentes só no modo ligado; login da conta funcionando (RF-04);
- comando: cria a conta sem staff; segunda execução restaura senha e flags sem duplicar
  (RF-05);
- comentário: aviso só no modo ligado; envio válido e envio pego pelo honeypot sem
  gravar e com a mensagem do modo; vazio e limite como hoje; modo desligado publicando
  (RF-06);
- o link da mensagem sai como `<a>` no HTML, não como texto escapado (RNF-03).
