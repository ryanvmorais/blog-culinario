---
feature: Limitação de taxa em login e comentários
status: concluído
date: 2026-09-12
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
  - 011-hospedagem/requirements.md
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
  **Superseded by** adendo desta spec, decisão resolvida 1 (Admin) e RF-05 (cadastro).
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

## Adendo (2026-11-16): login do Admin, cadastro e IPv6

> Status do adendo: concluído (2026-11-16). O texto acima é o aprovado em 2026-09-12 e fica como
> está; o adendo acrescenta requisitos, com a numeração continuando a dele.

**Contexto.** A spec 011 levou o contador para um cache em arquivo compartilhado entre
os workers e passou a identificar o visitante pelo `CF-Connecting-IP` atrás da
Cloudflare (RF-08 e RF-10 da 011). A auditoria de segurança de 2026-11-16 encontrou três
pontos em que o limite não cobre o que deveria (OWASP A07:2025, CWE-307 e CWE-770):

1. **O login do Admin não tem limite.** A tela de login do Admin (`<ADMIN_URL>login/`) é
   uma view do próprio Django, separada da `EntrarView`, e aceita tentativas sem
   contador. O não-objetivo "admin" acima e a decisão resolvida 10 da spec 011 tinham
   deixado esse limite de fora, confiando no caminho trocado (`ADMIN_URL`) mais a senha.
   O caminho trocado só esconde a tela, e ela protege a conta com mais permissão do site.
2. **O cadastro não tem limite.** Com o modo demonstração desligado (o padrão de quem
   clona), dá para criar contas sem parar. Com ele ligado, nada é gravado, mas o
   formulário continua respondendo, sem limite, se um nome de usuário já existe.
3. **O contador por IP é fácil de contornar.**
   - **IPv6:** a chave usa o endereço IPv6 completo. Uma conexão IPv6 comum recebe da
     operadora um bloco /64 inteiro, com mais endereços do que qualquer limite, e cada
     endereço do bloco ganha um contador zerado.
   - **Descarte do cache:** o cache em arquivo segue o `MAX_ENTRIES` padrão do Django
     (300). Acima disso, cada gravação apaga um terço dos arquivos ao acaso, e um
     contador ainda dentro da janela pode sumir com eles.

**Objetivos do adendo.**

- Limitar as tentativas no login do Admin, com o mesmo contador do login público.
- Limitar os envios do formulário de cadastro por IP numa janela de tempo.
- Contar os endereços IPv6 de uma mesma rede /64 como um visitante só.
- Manter os contadores ativos até o fim da janela, mesmo com muitos visitantes.

**Não-objetivos do adendo.**

- Bloqueio por conta (contar as falhas pelo nome de usuário), CAPTCHA ou segundo fator
  no Admin.
- Mudar os limites e as mensagens de RF-01 e RF-02.
- Limite nas páginas de leitura (home, listagem, detalhe, busca).
- Trocar o cache em arquivo por Redis ou por outro serviço.
- Mudar o que o `ip_do_visitante()` devolve (spec 011, RF-10): o agrupamento por rede
  vale só para a chave do contador.

**Personas do adendo.**

- Como **um atacante** testando senhas no Admin, devo ser barrado depois de poucas
  tentativas, como no login público.
- Como **o mantenedor** de uma cópia do blog sem o modo demonstração, não quero que um
  script crie contas em massa.
- Como **um visitante com IPv6**, quero o mesmo limite de quem usa IPv4: nem mais
  folgado, nem bloqueado por outra rede.
- Como **um visitante legítimo** que errou o formulário de cadastro algumas vezes, não
  quero ser bloqueado por um limite baixo demais.

### RF-04 — Limite de tentativas no login do Admin

- **Given** um IP que já fez o número máximo de tentativas de login na janela, somando
  as do login público (RF-01) e as do Admin
  **When** uma nova tentativa (POST) chega à tela de login do Admin
  **Then** ela é recusada sem conferir usuário e senha, e a tela de login do Admin volta
  com a mensagem "Muitas tentativas de login. Tente novamente em alguns minutos.".
- **Given** um IP abaixo do limite
  **When** faz login no Admin com usuário e senha certos de uma conta da equipe
  **Then** entra no Admin normalmente, e a tentativa soma ao contador.
- **Given** um IP que esgotou o limite no Admin
  **When** tenta o login público na mesma janela
  **Then** também é recusado: as duas telas dividem um contador só.
- **Given** qualquer `ADMIN_URL` (spec 011, RF-14)
  **When** o Admin está nesse caminho
  **Then** o limite vale na tela de login dele.
- **Given** a tela de login do Admin
  **When** é aberta por GET
  **Then** a visita não soma ao contador.

### RF-05 — Limite de envios do cadastro por IP

- **Given** um IP que já enviou o formulário de cadastro o número máximo de vezes na
  janela, com dados válidos ou não
  **When** um novo envio (POST) chega a `usuarios:cadastro`
  **Then** o formulário não é validado, nenhuma conta é criada, e a página de cadastro
  volta com a mensagem "Muitas tentativas de cadastro. Tente novamente mais tarde.".
- **Given** o modo demonstração ligado (spec 009)
  **When** o IP passa do limite
  **Then** vale a mesma recusa, antes da validação.
- **Given** o contador do cadastro
  **When** é contado
  **Then** fica separado do contador do login e do comentário.

### RF-06 — Uma rede IPv6 /64 conta como um visitante

Complementa o RNF-02: a chave continua sendo o endereço de rede, não o usuário.

- **Given** dois pedidos de endereços IPv6 diferentes dentro do mesmo /64
  **When** a limitação de taxa conta as tentativas
  **Then** os dois somam no mesmo contador.
- **Given** dois pedidos de endereços IPv6 em redes /64 diferentes
  **When** a limitação de taxa conta as tentativas
  **Then** cada rede tem o próprio contador.
- **Given** um endereço IPv4, ou um IPv4 escrito na forma IPv6 (`::ffff:a.b.c.d`)
  **When** a limitação de taxa conta as tentativas
  **Then** a chave é o endereço IPv4, como hoje.
- **Given** um identificador que não é endereço IP (o `"desconhecido"` da spec 011)
  **When** a limitação de taxa conta as tentativas
  **Then** ele é usado como está.

### RF-07 — Contador ativo não some antes do fim da janela

Complementa o RF-03: o contador zera ao fim da janela, e não antes.

- **Given** mais de 300 contadores de limite ativos ao mesmo tempo
  **When** um contador novo é criado
  **Then** os contadores ativos continuam valendo até o fim da janela de cada um.

### RNF-03 — Sem dependência nova no adendo

Vale o RNF-01: o reforço usa o `limite_excedido()`, o cache em arquivo da spec 011 e o
módulo `ipaddress` da biblioteca padrão. Nada de `django-axes`, `django-ratelimit` nem
Redis.

### RNF-04 — Comportamento atual preservado

RF-01 a RF-03 seguem com os limites, as janelas e as mensagens de hoje, e com o contador
compartilhado entre workers e atômico da spec 011 (RF-08). Os testes existentes desta
spec, da 007, da 009 e da 011 continuam passando sem mudança de comportamento.

### RNF-05 — Admin sem mudança visível abaixo do limite

Abaixo do limite, o login do Admin é o do Django: o mesmo formulário, o mesmo
redirecionamento para `next` e as mesmas mensagens de erro de senha.

**Decisões resolvidas do adendo.**

1. **Login do Admin com limite** (2026-11-16). Reverte a decisão resolvida 10 da
   spec 011 e o não-objetivo "admin" acima: o caminho trocado continua, como segunda
   camada, e o login do Admin passa a ter o mesmo limite do login público.
2. **Um contador para as duas telas de login** (2026-11-16). Contadores separados
   dariam o dobro de tentativas por janela a quem alternasse entre as telas.
3. **Cadastro: 10 envios por hora** (2026-11-16). Fica acima do login (5 em 5
   minutos) porque o visitante da demonstração costuma enviar o formulário algumas
   vezes para ver a validação, e baixo o bastante para impedir conta em massa.
4. **Teto do cache: 10.000 entradas** (2026-11-16). Cabe com folga no volume e fica
   muito acima dos visitantes simultâneos de um blog.

### RF-08 — A suíte cobre o adendo

- Admin: a tentativa acima do limite é recusada sem autenticar, e a mensagem aparece;
  abaixo do limite, o login da equipe funciona; o limite esgotado numa tela vale na
  outra; o GET não soma; o limite vale com um `ADMIN_URL` diferente do padrão.
- Cadastro: o envio acima do limite não cria conta, com o modo demonstração ligado e
  desligado; o contador do cadastro não interfere no do login.
- IPv6: dois endereços do mesmo /64 dividem o contador; de /64 diferentes, não; IPv4 e
  IPv4 na forma IPv6 mantêm a chave de hoje.
- Cache: com mais de 300 contadores ativos, um contador antigo dentro da janela
  continua valendo depois de criados outros.
