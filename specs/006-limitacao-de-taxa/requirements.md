---
feature: Limitação de taxa em login e comentários
status: concluído
date: 2026-09-12
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
origin: concepcao
---

# 006 — Limitação de taxa em login e comentários

## Contexto e problema

A auditoria de segurança rodada em 2026-09-12 encontrou um achado MÉDIO
(CWE-307, OWASP A07:2021): nem o login (`usuarios:entrar`) nem a criação de
comentário (`receitas:comentar`) têm qualquer limite de tentativas. Um
atacante pode tentar senhas indefinidamente contra uma conta conhecida
(brute force/credential stuffing), e qualquer usuário autenticado pode
inundar uma receita de comentários via POSTs repetidos, sem nenhum limite
de taxa.

Django não inclui rate limiting por padrão. Esta spec resolve os dois
pontos com a menor infraestrutura possível — sem introduzir uma
dependência nova, usando o backend de cache já disponível no projeto.

## Objetivos

- Limitar tentativas de login por IP numa janela de tempo.
- Limitar criação de comentários por IP numa janela de tempo.
- Mensagem de erro clara ao usuário quando o limite é atingido.
- Funcionar com o backend de cache padrão do Django (`LocMemCache`, sem
  configuração adicional) — coerente com a stack mínima do projeto.

## Não-objetivos

- Bloqueio permanente de conta ou IP (banimento) — só desaceleração
  temporária dentro da janela.
- Rate limiting em outros endpoints (busca, listagem, admin) — fora do
  escopo dos achados da auditoria.
- CAPTCHA ou verificação humana adicional.
- Rate limiting distribuído entre múltiplos processos/workers via Redis —
  fora de escopo enquanto o deploy (PythonAnywhere) não exigir isso.

## Personas

- Como **um atacante** tentando adivinhar a senha de outra conta, devo ser
  barrado depois de poucas tentativas dentro de uma janela curta.
- Como **o mantenedor** do blog, quero que um script não consiga inundar
  uma receita de comentários automatizados.
- Como **um visitante legítimo** que errou a senha 2-3 vezes, não quero ser
  bloqueado incorretamente por um limite baixo demais.

## Requisitos funcionais

### RF-01 — Limite de tentativas de login por IP

- **Given** um IP já fez o número máximo de tentativas de POST em
  `/usuarios/entrar/` dentro da janela de tempo configurada
  **When** uma tentativa adicional chega dentro da mesma janela
  **Then** a view responde com uma mensagem de erro ("Muitas tentativas de
  login. Tente novamente em alguns minutos.") sem validar usuário/senha —
  a tentativa bloqueada não é processada pelo `AuthenticationForm`.

### RF-02 — Limite de criação de comentários por IP

- **Given** um IP já publicou o número máximo de comentários (em qualquer
  receita) dentro da janela de tempo configurada
  **When** uma tentativa adicional de POST em `receitas:comentar` chega
  dentro da mesma janela
  **Then** o comentário não é salvo e uma mensagem de erro é mostrada
  ("Você está comentando rápido demais. Aguarde um instante.").

### RF-03 — Contador expira automaticamente

- **Given** a janela de tempo configurada para cada limite
  **When** o tempo da janela passa sem novas tentativas
  **Then** o contador zera e novas tentativas voltam a ser aceitas
  normalmente, sem intervenção manual.

## Requisitos não-funcionais

### RNF-01 — Sem dependência nova

A limitação usa o backend de cache já embutido no Django (default
`LocMemCache` quando `CACHES` não está configurado), sem adicionar
`django-ratelimit`, `django-axes` ou Redis — consistente com a filosofia
de stack mínima do projeto (ver `docs/stack.md`, ADR-3 da spec 000).

### RNF-02 — Chave de limitação por IP, não por usuário

A chave de limitação é `REMOTE_ADDR`, não o username/usuário submetido —
evita que um atacante contorne o limite variando o username testado a
cada tentativa.

## Perguntas em aberto

- Valores exatos dos limites (proposta para o design: 5 tentativas de
  login por 5 minutos; 5 comentários por 1 minuto) — ajustáveis se você
  preferir outros números.
- `REMOTE_ADDR` pode não refletir o IP real do visitante atrás de um proxy
  reverso, dependendo de como o PythonAnywhere expõe a requisição
  (`X-Forwarded-For`) — decisão adiada para a spec de deploy, quando a
  infraestrutura real estiver definida.

## Testes

Cobertura planejada (etapa própria em `tasks.md`, não pulada):
- Login: N tentativas dentro da janela bloqueiam a N+1; após a janela
  expirar (mock de tempo ou janela curta em teste), tentativas voltam a
  ser aceitas; tentativa bloqueada não altera `is_authenticated`.
- Comentário: mesma lógica, verificando que o comentário bloqueado não é
  persistido no banco.
- Isolamento entre IPs: dois IPs distintos não compartilham o mesmo
  contador.
