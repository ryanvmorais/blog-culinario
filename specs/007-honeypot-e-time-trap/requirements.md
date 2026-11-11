---
feature: Honeypot e time-trap no formulário de comentário
status: concluído
date: 2026-09-12
related:
  - 005-comentarios/requirements.md
  - 006-limitacao-de-taxa/requirements.md
origin: concepcao
---

# 007 — Honeypot e time-trap no formulário de comentário

## Contexto e problema

A spec 006 limitou a *taxa* de comentários por IP (5/minuto), mas não
distingue humano de bot — um bot lento (ou distribuído entre poucos IPs)
ainda consegue publicar spam dentro do limite. Esta spec acrescenta duas
heurísticas baratas e sem dependência nova, específicas do formulário de
comentário (`receitas/templates/receitas/detalhe.html`), que filtram bots
*antes* de consumir uma tentativa do limite de taxa:

- **Honeypot**: um campo extra, invisível para humanos, que só um bot que
  preenche todo `<input>` do HTML preencheria.
- **Time-trap**: rejeita um POST que chega rápido demais depois do GET que
  renderizou o formulário — tempo incompatível com alguém lendo e
  digitando um comentário.

Nasce como spec própria (007), não como reabertura da 006 — a 006 já está
`concluído` e mergeada; specs concluídas são histórico imutável do
projeto (ver `specs/README.md`).

## Objetivos

- Rejeitar silenciosamente um POST que preencheu o campo-armadilha
  (honeypot).
- Rejeitar um POST que chegou antes de um tempo mínimo plausível
  (time-trap).
- Nenhuma das duas heurísticas pode incomodar um usuário humano real,
  incluindo quem usa leitor de tela ou autofill do navegador.
- Sem dependência nova — reaproveita `FormularioComentario`
  (`receitas/forms.py`) e o cache já usado pela spec 006 para carimbar o
  tempo de renderização.

## Não-objetivos

- Aplicar honeypot/time-trap ao formulário de login ou cadastro — login
  não é superfície de spam de conteúdo (é tentativa de credencial, já
  coberta pela spec 006); cadastro fica de fora deste escopo, candidato a
  spec futura se o volume de contas-spam justificar.
- CAPTCHA ou verificação humana explícita.
- Qualquer heurística baseada em terceiros (Akismet, reCAPTCHA) — mantém
  a filosofia de stack mínima do projeto.

## Personas

- Como **um bot simples** que preenche todo campo do HTML de um
  formulário, devo ser barrado sem perceber (resposta idêntica à de
  sucesso, sem revelar que fui detectado).
- Como **um bot rápido** que só preenche o campo `texto` e envia
  imediatamente, devo ser barrado pelo tempo mínimo decorrido.
- Como **um usuário humano**, incluindo quem usa leitor de tela ou
  autofill, meu comentário nunca deve ser rejeitado por engano.

## Requisitos funcionais

### RF-01 — Campo honeypot rejeita bots que preenchem tudo

- **Given** o formulário de comentário renderizado inclui um campo extra,
  visualmente oculto e fora da ordem de tabulação
  **When** o POST chega com esse campo preenchido (não vazio)
  **Then** o comentário não é salvo, mas a resposta é indistinguível de
  um envio bem-sucedido (mesmo redirect, sem mensagem de erro) — não dá
  ao bot um sinal de que foi detectado.

### RF-02 — Time-trap rejeita envios rápidos demais

- **Given** o GET que renderizou o formulário registrou um carimbo de
  tempo
  **When** o POST correspondente chega antes de um tempo mínimo
  configurado (proposta para o design: 2 segundos)
  **Then** o comentário não é salvo, com o mesmo comportamento
  silencioso do RF-01.

### RF-03 — Nenhum falso positivo em uso humano normal

- **Given** um visitante humano preenche e envia o formulário
  normalmente (incluindo autofill de navegador ou tempo de leitura antes
  de comentar)
  **When** o POST chega
  **Then** o comentário é criado normalmente — nem o honeypot nem o
  time-trap disparam.

## Requisitos não-funcionais

### RNF-01 — Sem dependência nova

Honeypot é um campo de formulário comum; time-trap usa o cache já
introduzido pela spec 006 (`blog_culinario/limitacao.py` ou um carimbo de
tempo assinado) — nenhuma biblioteca de terceiros.

### RNF-02 — Acessível por construção

O campo honeypot usa ocultação que não afeta leitor de tela de forma
enganosa: `position: absolute; left: -9999px` (ou técnica equivalente) +
`tabindex="-1"` + `autocomplete="off"` + um `name` que não corresponda a
um campo real (evita autofill do navegador preenchê-lo por engano).

### RNF-03 — Falha silenciosa, não punitiva

Nem o honeypot nem o time-trap devem consumir uma tentativa do limite de
taxa da spec 006, nem gerar uma mensagem de erro visível — o objetivo é
que o bot não aprenda que foi filtrado.

## Perguntas em aberto

- Tempo mínimo exato do time-trap (proposta: 2 segundos) — ajustável se
  se mostrar baixo/alto demais na prática.
- Onde carimbar o tempo de renderização: campo hidden com timestamp
  assinado (`django.core.signing`) vs. entrada no cache por sessão — a
  decidir no design.

## Testes

Cobertura planejada (etapa própria em `tasks.md`, não pulada):
- Honeypot preenchido não cria comentário, mas resposta parece sucesso.
- POST antes do tempo mínimo não cria comentário.
- POST humano normal (honeypot vazio, tempo plausível) cria o comentário.
- Nenhuma das duas heurísticas consome o limite de taxa da spec 006.
