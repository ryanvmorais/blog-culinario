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

## Adendo (2026-11-16): login do Admin, cadastro e IPv6

> Status do adendo: concluído (2026-11-16). Desenha os RF-04 a RF-08 e os RNF-03 a RNF-05 do adendo
> do `requirements.md`. O texto acima fica como está; os ADRs continuam a numeração.

### Visão geral da abordagem do adendo

O `limite_excedido()` continua sendo a única porta da limitação de taxa, e o adendo o
aplica em mais dois lugares e o torna mais difícil de contornar:

- **Admin:** o site do Admin passa a ser uma subclasse do `AdminSite` do Django, ligada
  pelo `default_site` de um `AdminConfig` do projeto. O `login()` dela chama o
  `limite_excedido()` com o namespace `"login"` antes de delegar ao `login()` original,
  e por isso divide o contador com a `EntrarView` (decisão resolvida 2).
- **Cadastro:** a `CadastroView` ganha um `post()` que checa o namespace `"cadastro"`
  antes de validar o formulário, no mesmo desenho da `EntrarView`.
- **IPv6:** a chave do contador deixa de ser o endereço que o `ip_do_visitante()`
  devolve e passa a ser o identificador de rede dele: o próprio endereço no IPv4, o /64
  no IPv6.
- **Cache:** o `CACHES` ganha `MAX_ENTRIES` de 10.000, e o descarte aleatório do
  `FileBasedCache` só volta a acontecer muito acima do uso real.

### Componentes do adendo

#### `blog_culinario/limitacao.py`

- **Constantes do login:** `LIMITE_LOGIN = 5`, `JANELA_LOGIN_SEGUNDOS = 300` e
  `MENSAGEM_LIMITE_LOGIN` (o texto do RF-01). Saem da `EntrarView` porque agora duas
  telas usam os mesmos valores.
- **`_identificador_de_rede(ip: str) -> str`** (privada): devolve a chave do visitante
  (RF-06).
  - Endereço que não é IP (o `"desconhecido"`): volta como está.
  - IPv6 com um IPv4 dentro (`::ffff:a.b.c.d`): o IPv4.
  - Outro IPv6: a rede /64 em texto (`2001:db8:1:2::/64`).
  - IPv4: o endereço normalizado.
- **`limite_excedido()`:** a chave passa a ser
  `limite:<namespace>:<identificador de rede>`. Assinatura, efeito colateral e contrato
  ficam iguais (RNF-04).

#### `blog_culinario/site_admin.py` (módulo novo)

- **`SiteAdminComLimite(AdminSite)`:** sobrescreve
  `login(request, extra_context=None)`. No POST, se
  `limite_excedido(request, "login", LIMITE_LOGIN, JANELA_LOGIN_SEGUNDOS)` for
  verdadeiro, grava `MENSAGEM_LIMITE_LOGIN` com `messages.error` e redireciona para
  `request.get_full_path()`. O redirecionamento mantém o `?next=`, e o template de login
  do Admin já mostra as mensagens (RF-04). Nos outros casos, delega ao `super().login()`
  (RNF-05). O GET não passa pelo contador.
- **`ConfigAdmin(AdminConfig)`:** só define
  `default_site = "blog_culinario.site_admin.SiteAdminComLimite"`. O rótulo do app
  continua `admin`, então templates, estáticos, `reverse("admin:...")` e cada
  `@admin.register` dos apps seguem iguais.

#### `blog_culinario/settings/base.py`

- `INSTALLED_APPS`: `"django.contrib.admin"` vira `"blog_culinario.site_admin.ConfigAdmin"`.
- `CACHES["default"]` ganha `"OPTIONS": {"MAX_ENTRIES": 10_000}` (RF-07, decisão
  resolvida 4).

#### `usuarios/views.py`

- **`EntrarView.post()`:** passa a usar as constantes do `limitacao.py`, com o mesmo
  comportamento.
- **`CadastroView.post()`** (novo): se
  `limite_excedido(request, "cadastro", limite=10, janela_segundos=3600)`, grava a
  mensagem do RF-05 e redireciona para `usuarios:cadastro`. Senão, segue o
  `FormView.post()` (RF-05, decisão resolvida 3). A checagem vem antes do formulário,
  então também vale no modo demonstração.

### Interfaces do adendo

Nenhuma rota nova. Mudam só as respostas acima do limite:

| Pedido | Acima do limite |
|---|---|
| POST no login do Admin | 302 para a mesma URL (com `?next=`), mensagem do RF-01 |
| POST em `/usuarios/cadastro/` | 302 para `/usuarios/cadastro/`, mensagem do RF-05 |

### ADR-5 — O limite do Admin mora no site do Admin, não numa rota na frente

**Decisão.** Subclasse do `AdminSite`, ligada pelo `default_site` de um `AdminConfig`
(o caminho que a documentação do Django indica para trocar o site padrão do Admin).
**Alternativas.** (a) Uma rota `<ADMIN_URL>login/` declarada antes do
`admin.site.urls`, apontando para uma view que limita e delega. (b) Um middleware que
confere o caminho do login do Admin. (c) `django-axes`.
**Porquê.** O `login()` do site é a única entrada do login do Admin, qualquer que seja
o caminho. A rota da frente depende da ordem do `urlpatterns`, e o middleware, do
caminho. O `django-axes` é dependência nova (RNF-03).
**Trade-off.** O `INSTALLED_APPS` troca o app do Admin pela configuração do projeto, e
quem lê o código precisa saber do `default_site` para achar o limite.

### ADR-6 — O agrupamento por rede fica na chave do contador

**Decisão.** O `/64` é calculado dentro do `limite_excedido()`, e o
`ip_do_visitante()` continua devolvendo o endereço completo.
**Alternativas.** Devolver a rede já no `ip_do_visitante()`.
**Porquê.** O RF-10 da spec 011 define o que o `ip_do_visitante()` devolve, e o
agrupamento é uma regra da limitação, não da identificação do visitante.
**Trade-off.** Nenhum relevante: hoje só a limitação usa o `ip_do_visitante()`.

### ADR-7 — Prefixo /64 no IPv6

**Decisão.** Agrupar o IPv6 pelo /64.
**Alternativas.** /56 ou /48, os blocos que muitas operadoras entregam a cada cliente
residencial.
**Porquê.** O /64 é a menor rede que uma operadora entrega a um cliente, então nunca
junta dois clientes num contador. Um prefixo maior juntaria, nas operadoras móveis,
aparelhos de pessoas diferentes.
**Trade-off.** Quem recebe um /56 tem até 256 redes /64, cada uma com o próprio
contador. O limite continua finito, contra o ilimitado de hoje.

### ADR-8 — Teto no cache de hoje, sem um cache só para os limites

**Decisão.** `MAX_ENTRIES` de 10.000 no `CACHES["default"]`.
**Alternativas.** Um segundo cache (`CACHES["limites"]`) só para os contadores.
**Porquê.** A limitação de taxa é o único uso do cache do projeto, e um segundo cache
seria mais uma pasta e mais uma configuração para quem clona.
**Trade-off.** Um uso novo do cache divide o mesmo teto. Quem acrescentar um revê o
`MAX_ENTRIES` ou separa os caches.

### Impacto no código existente do adendo

- `blog_culinario/site_admin.py`: arquivo novo.
- `blog_culinario/limitacao.py`: constantes do login, `_identificador_de_rede()` e a
  chave nova. Os contadores que estiverem no cache durante o deploy ficam órfãos e
  expiram sozinhos na janela deles.
- `blog_culinario/settings/base.py`: `INSTALLED_APPS` e `CACHES`.
- `usuarios/views.py`: `EntrarView` com as constantes e `CadastroView.post()` novo.
- Specs: a decisão resolvida 10 da 011 e o não-objetivo "admin" desta spec ganham a
  linha `**Superseded by**` apontando o adendo.
- Documentação: o mapa do `CLAUDE.md` (a linha do `limitacao.py`) e a frase da
  limitação de taxa nos dois READMEs passam a citar o Admin e o cadastro.

### Estratégia de testes do adendo

Arquivo novo `nucleo/test_limitacao.py`, para o que cruza os apps (Admin, IPv6 e
cache), e `usuarios/tests.py`, para o cadastro, ao lado dos testes do login. Todos com
`cache.clear()` antes de cada teste, como os de hoje.

- **Admin (RF-04):**
  - cinco POSTs errados em `reverse("admin:login")` e o sexto recusado, sem autenticar
    e com a mensagem;
  - um login de staff abaixo do limite entra no Admin;
  - o limite esgotado no Admin recusa o login público, e o contrário também;
  - o GET não soma;
  - `admin.site` é um `SiteAdminComLimite`;
  - um `ROOT_URLCONF` de teste que monta o `admin.site.urls` em outro caminho mantém o
    limite.
- **Cadastro (RF-05):** dez POSTs e o 11º recusado, sem criar o usuário, com o modo
  demonstração ligado e desligado (`override_settings(MODO_DEMONSTRACAO=...)`); o
  contador do cadastro esgotado não recusa o login.
- **IPv6 (RF-06):** unidade do `_identificador_de_rede()` (IPv4, IPv4 na forma IPv6,
  dois endereços do mesmo /64, /64 diferentes, `"desconhecido"`) e um teste de ponta a
  ponta: dois `REMOTE_ADDR` do mesmo /64 dividem o contador do login.
- **Cache (RF-07):** um contador no limite, depois 400 contadores de outros IPs pelo
  `limite_excedido()`, e o primeiro ainda recusado.
- **Regressão (RNF-04):** a suíte inteira, sem mudar os testes da 006, 007, 009 e 011.

### Desvios do adendo

1. **`conftest.py` herda o `CACHES` do projeto** (RF-07, ADR-8). A suíte montava um
   `CACHES` próprio, só com o backend e a pasta, e rodaria com o teto padrão de 300.
   O `_caches()` passou a copiar o `CACHES["default"]` das configurações e trocar só a
   pasta, para o teste do RF-07 medir o `MAX_ENTRIES` real.
2. **600 contadores no teste do cache, e não 400** (RF-07). Com o teto padrão, o
   contador esgotado sobreviveria a 400 contadores novos em cerca de 44% das
   execuções; com 600, em cerca de 20%. O teste fica mais sensível à regressão, e
   continua rápido.

### Notas de implementação do adendo

- Suíte: 322 testes antes do adendo, 344 depois (22 novos: 19 em
  `nucleo/test_limitacao.py`, 3 em `usuarios/tests.py`); os testes da 006, 007, 009 e
  011 passaram sem mudança (RNF-04).
- A chave do contador muda de formato só no IPv6 (`limite:login:2001:db8:1:2::/64`); o
  IPv4 fica como antes, então os contadores IPv4 do cache seguem valendo no deploy.
- O login do Admin abaixo do limite é o do Django (RNF-05). O teste manda o `next` como
  o formulário do Admin, que o envia num campo oculto.

## Adendo 2 (2026-11-16): registro no log

> Status do adendo 2: concluído (2026-11-16). Desenha o RF-09, o RF-10 e o RNF-06 do adendo 2 do
> `requirements.md`. Os ADRs continuam a numeração.

### Visão geral da abordagem do adendo 2

O `limite_excedido()` ganha um logger do próprio módulo
(`logging.getLogger(__name__)`, o `blog_culinario.limitacao`) e escreve um `WARNING`
quando o número que o `incr()` devolveu é exatamente `limite + 1`. É a primeira
tentativa recusada da janela: o `incr()` é atômico entre os workers (spec 011, RF-08) e
dá a cada pedido um número só seu, então um pedido só por janela vê esse número. O
`LOGGING` de produção já leva o `WARNING` do logger raiz ao console.

### Componentes do adendo 2

#### `blog_culinario/limitacao.py`

- `logger = logging.getLogger(__name__)` na seção de constantes.
- Depois do `incr()`: se `tentativas == limite + 1`,
  `logger.warning("limite atingido: %s %s", chave, request.path)`. O `request.path` não
  traz a query string, e nenhum dado do visitante entra na linha (RNF-06).
- O retorno e o resto do contrato ficam iguais (RNF-04).

### ADR-9 — A primeira recusa se reconhece pelo número do contador

**Decisão.** Registrar quando `tentativas == limite + 1`, sem estado novo.
**Alternativas.** (a) Uma chave extra no cache (`add()` de um marcador "já registrado"
com a validade da janela). (b) Registrar toda recusa.
**Porquê.** O número exato já existe e é único por pedido, graças ao `incr()` atômico; a
chave extra seria mais uma gravação no cache por recusa. Registrar toda recusa inundaria
o log num ataque (decisão resolvida 2 do adendo 2).
**Trade-off.** Se o contador expirar entre o `add()` e o `incr()` (o ramo do
`ValueError`), a janela recomeça e a primeira recusa dela é registrada normalmente:
nenhuma perda.

### Impacto no código existente do adendo 2

- `blog_culinario/limitacao.py`: o logger e as duas linhas do registro.
- Nenhuma mudança no `LOGGING`, nas views nem nos testes de hoje.

### Estratégia de testes do adendo 2

Em `nucleo/test_limitacao.py`, com o `caplog` do pytest no logger
`blog_culinario.limitacao`:

- Cinco tentativas de login sem registro; a sexta gera um `WARNING` com `limite
  atingido: login /usuarios/entrar/`; a sétima não gera outro.
- A linha não contém o `REMOTE_ADDR` do pedido nem o nome de usuário enviado.
- No cadastro, a 11ª tentativa gera a linha com `cadastro` e o caminho dele.
