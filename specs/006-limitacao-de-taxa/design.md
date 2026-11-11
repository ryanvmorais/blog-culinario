---
feature: Limitação de taxa em login e comentários
status: concluído
date: 2026-09-12
related:
  - 004-autenticacao/requirements.md
  - 005-comentarios/requirements.md
origin: concepcao
---

# 006 — Limitação de taxa em login e comentários — design

## Visão geral da abordagem

Uma função só (`limite_excedido`), compartilhada pelas duas views afetadas,
conta tentativas por IP no backend de cache do Django (`LocMemCache` por
padrão, sem `CACHES` configurado) usando uma chave `limite:<namespace>:<ip>`
com TTL igual à janela de tempo. Cada view chama a função no início do
`post()`: se o limite já foi atingido, responde com uma mensagem de erro e
não processa a tentativa; caso contrário, segue o fluxo normal.

## Componentes

### `blog_culinario/limitacao.py` (módulo novo)

Vive no pacote do projeto, não dentro de `usuarios/` ou `receitas/` — é
compartilhado pelos dois apps, e nenhum dos dois deveria importar do outro
(ver ADR-1). Expõe uma única função:

```python
def limite_excedido(request: HttpRequest, chave: str, limite: int, janela_segundos: int) -> bool
```

- `chave` — namespace do limite (`"login"`, `"comentario"`) para os dois
  contadores nunca colidirem.
- Identifica o requisitante por `request.META["REMOTE_ADDR"]` (RNF-02).
- Usa `cache.add()` (só define se a chave não existir, preservando o TTL
  original) seguido de `cache.incr()` (atômico) — o par é o idiom padrão do
  Django para contadores com expiração automática (RF-03).

### `usuarios/views.py::EntrarView`

`post()` passa a checar `limite_excedido(request, "login", limite=5,
janela_segundos=300)` antes de delegar ao `LoginView.post()` nativo. Bloqueado
→ mensagem de erro + redirect para `usuarios:entrar`, sem tocar no
`AuthenticationForm` (RF-01).

### `receitas/views.py::ComentarioCreateView`

`post()` passa a checar `limite_excedido(request, "comentario", limite=5,
janela_segundos=60)` antes de buscar a receita/validar o formulário.
Bloqueado → mensagem de erro + o mesmo redirect com `#comentarios` que o
fluxo de erro de validação já usa (RF-02).

## Modelo de dados

Nenhum. O estado do contador é efêmero (cache), não persiste no banco —
coerente com o objetivo de só desacelerar, nunca banir (não-objetivo).

## Interfaces

Nenhuma URL nova. Comportamento adicional nos dois endpoints existentes:

| Método | URL | View | Mudança |
|---|---|---|---|
| POST | `/usuarios/entrar/` | `usuarios.views.EntrarView` | Bloqueia a partir da 6ª tentativa em 5 min por IP |
| POST | `/receitas/<slug>/comentar/` | `receitas.views.ComentarioCreateView` | Bloqueia a partir do 6º comentário em 1 min por IP |

## ADRs

### ADR-1 — Módulo compartilhado no pacote do projeto, não em um app

**Decisão.** `blog_culinario/limitacao.py`, importado por `usuarios` e por
`receitas`.
**Alternativas.** Duplicar a função em cada app (zero acoplamento novo, mas
repete lógica idêntica); criar um app `comum`/`core` só para isso.
**Porquê.** É uma função pequena e sem estado próprio, usada por exatamente
dois apps de domínio que não deveriam depender um do outro — o pacote do
projeto é o único lugar comum a ambos sem criar essa dependência cruzada. Um
app novo só para uma função seria estrutura demais para o problema.
**Trade-off.** `usuarios`/`receitas` passam a importar de `blog_culinario`
(normalmente só settings/urls) — aceitável porque é infraestrutura
transversal, não lógica de domínio.

### ADR-2 — Cache builtin do Django, sem biblioteca de rate limiting

**Decisão.** `cache.add()` + `cache.incr()` do `django.core.cache`, sem
`django-ratelimit`/`django-axes`.
**Alternativas.** `django-ratelimit` (decorator pronto, bem testado);
`django-axes` (especializado em login, com bloqueio configurável e painel no
admin).
**Porquê.** RNF-01: zero dependência nova, e o valor didático de mostrar como
implementar rate limiting a partir do cache framework que o Django já expõe —
uma biblioteca pronta esconderia exatamente o que este repositório existe
para ensinar.
**Trade-off.** Sem desbloqueio manual via admin, sem métricas prontas, e o
contador reseta se o processo do `LocMemCache` reiniciar — todos aceitáveis
porque o objetivo é só desacelerar abuso simples, não uma defesa
industrial.

### ADR-3 — Chave por IP, não por usuário

**Decisão.** `REMOTE_ADDR` é o único identificador do contador (RNF-02, já
fixado em requirements).
**Alternativas.** Chave por username tentado (mais granular por conta).
**Porquê.** Um atacante que varia o username a cada tentativa nunca atingiria
o limite de nenhum username individual — agregar por IP fecha essa lacuna.
**Trade-off.** Vários usuários atrás do mesmo IP público (rede
corporativa/escolar, NAT) compartilham o mesmo contador — um pico de erros de
um visitante pode bloquear temporariamente os demais atrás do mesmo IP.
Aceitável dado o volume esperado de um blog pessoal; reavaliar se o tráfego
real mostrar esse efeito colateral.

### ADR-4 — Mesmo limite aplicado às duas superfícies apontadas pela auditoria

**Decisão.** Login e criação de comentário usam a mesma função, com janelas e
limites próprios por namespace (não compartilham contador entre si).
**Alternativas.** Resolver só o achado de login (mais crítico) e deixar
comentário para depois.
**Porquê.** A auditoria (2026-09-12) apontou os dois no mesmo achado MÉDIO;
resolver os dois juntos evita reabrir a mesma spec para o segundo caso.
**Trade-off.** Nenhum relevante — é a mesma primitiva reaplicada.

## Impacto no código existente

- `blog_culinario/limitacao.py` — arquivo novo.
- `usuarios/views.py` — `EntrarView` ganha `post()` (hoje só tem
  `form_valid()`).
- `receitas/views.py` — `ComentarioCreateView.post()` ganha a checagem no
  início, antes do `get_object_or_404`.

## Estratégia de testes

- `usuarios/tests.py`: `cache.clear()` em `setUp`/fixture (o contador não
  pode vazar entre testes); 5 tentativas de login com senha errada seguidas
  da 6ª (ainda dentro da janela) mostrando a mensagem de bloqueio e sem
  processar o `AuthenticationForm`; uma tentativa dentro do limite com
  credenciais corretas ainda autentica normalmente; dois IPs diferentes
  (`client.post(..., REMOTE_ADDR="10.0.0.2")`) não compartilham o contador.
- `receitas/tests.py`: mesmo padrão — 5 comentários seguidos do 6º bloqueado
  (comentário não é persistido), dentro do limite persiste normalmente,
  dois IPs não compartilham contador.
- `cache.clear()` também previne que a ordem de execução dos testes influencie
  o resultado (pytest-django não isola o cache entre testes por padrão).
