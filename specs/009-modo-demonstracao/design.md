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

# 009 — Modo demonstração — design

## Visão geral da abordagem

Uma setting booleana, `MODO_DEMONSTRACAO`, lida do ambiente em `settings/base.py` com
`False` por padrão. Um módulo novo, `blog_culinario/demonstracao.py`, concentra tudo o que
o modo precisa: as credenciais da conta pública, o endereço do repositório, os dois textos
de mensagem pós-envio e um context processor que entrega aos templates o estado do modo.

O comportamento muda só no ponto em que a view grava (ADR-1): o `CadastroView` e o
`ComentarioCreateView` continuam validando como hoje e, com o modo ligado, trocam o
`save()` por uma mensagem `info`. Os templates de cadastro, login e detalhe da receita
mostram o aviso fixo quando o context processor diz que o modo está ligado. A conta
`visitante` nasce de um management command idempotente.

## Layout de módulos

| Arquivo | Muda | O quê |
|---|---|---|
| `blog_culinario/settings/base.py` | muda | `MODO_DEMONSTRACAO` e o context processor |
| `blog_culinario/demonstracao.py` | novo | constantes, mensagens e context processor |
| `usuarios/views.py` | muda | `CadastroView.form_valid` |
| `usuarios/management/commands/criar_conta_demonstracao.py` | novo | conta `visitante` (com os `__init__.py` dos pacotes) |
| `receitas/views.py` | muda | `ComentarioCreateView.post` |
| `usuarios/templates/usuarios/cadastro.html` | muda | aviso antes do formulário |
| `usuarios/templates/usuarios/login.html` | muda | caixa com as credenciais |
| `receitas/templates/receitas/detalhe.html` | muda | aviso dentro do formulário de comentário |
| `static/css/tokens.css` | muda | token `--fonte-mono` |
| `static/css/base.css` | muda | link dentro de mensagem, `.aviso-demonstracao`, `.credenciais` |
| `docs/design-system.html` | muda | exemplo do aviso e das credenciais |
| `.github/workflows/lighthouse.yml` | muda | servidor auditado com o modo ligado |
| `.env.example`, `README.md`, `README.en.md`, `CLAUDE.md`, `specs/README.md` | muda | documentação e roadmap |
| `usuarios/test_modo_demonstracao.py`, `receitas/test_modo_demonstracao.py` | novo | testes |
| `nucleo/test_tema_escuro.py` | muda | par de contraste do link na mensagem |

## Modelo de dados

Nenhuma mudança de modelo nem migration. A conta de demonstração é um `User` comum
(`django.contrib.auth`), criado pelo comando do RF-05.

## Componentes

### `blog_culinario/settings/base.py`

```python
MODO_DEMONSTRACAO = env.bool("MODO_DEMONSTRACAO", default=False)
```

E `"blog_culinario.demonstracao.contexto_demonstracao"` no fim da lista de
`context_processors` (RF-01). O `prod.py` não força nada: quem liga é a variável do
ambiente da instância pública.

### `blog_culinario/demonstracao.py`

```python
USUARIO_DEMONSTRACAO = "visitante"
SENHA_DEMONSTRACAO = "receitas-demo"
URL_REPOSITORIO = "https://github.com/ryanvmorais/blog-culinario"

def modo_demonstracao_ligado() -> bool
def mensagem_cadastro() -> SafeString
def mensagem_comentario() -> SafeString
def contexto_demonstracao(request: HttpRequest) -> dict[str, object]
```

- `modo_demonstracao_ligado()` lê `settings.MODO_DEMONSTRACAO` na hora da chamada, não na
  importação, para o `override_settings` dos testes valer.
- `mensagem_cadastro()` e `mensagem_comentario()` montam os textos do RF-03 e do RF-06 com
  `format_html`, com o link para `URL_REPOSITORIO` (`target="_blank" rel="noopener"`, como
  o link do rodapé). Só interpolam constantes (ADR-2).
- `contexto_demonstracao()` devolve `{"modo_demonstracao": False}` com o modo desligado e,
  ligado, `{"modo_demonstracao": True, "conta_demonstracao": {"usuario": ..., "senha":
  ...}}` (ADR-3). As credenciais só existem no contexto com o modo ligado.

### `usuarios/views.py::CadastroView.form_valid`

```python
if modo_demonstracao_ligado():
    messages.info(self.request, mensagem_cadastro())
    return redirect("usuarios:cadastro")
```

Antes do `form.save()`. O formulário já passou por toda a validação do
`FormularioCadastro` (RNF-02); com o modo ligado, nada é gravado e a sessão segue anônima
(RF-03). O redirect segue o padrão post/redirect/get (ADR-4). Com o modo desligado, o
caminho de hoje fica intacto.

### `usuarios/management/commands/criar_conta_demonstracao.py`

`get_or_create(username=USUARIO_DEMONSTRACAO)` e, criada ou não, `set_password
(SENHA_DEMONSTRACAO)`, `is_active=True`, `is_staff=False`, `is_superuser=False` e
`save()` (RF-05). Escreve no `stdout` "Conta de demonstração criada." ou "Conta de
demonstração atualizada.". Com o modo desligado, roda do mesmo jeito e acrescenta um
aviso (`self.style.WARNING`) de que a conta publica comentários de verdade enquanto o modo
estiver desligado (ADR-6).

### `receitas/views.py::ComentarioCreateView`

Um método novo, `_confirmar_envio(request)`, registra a mensagem de envio aceito:
`messages.info(request, mensagem_comentario())` com o modo ligado e
`messages.success(request, "Comentário publicado!")` com ele desligado. O `post()` o usa
nos dois pontos que hoje dizem "Comentário publicado!":

- no ramo do honeypot e do time-trap, para o falso sucesso imitar o sucesso daquele
  ambiente (RF-06, decisão resolvida 6);
- no ramo do formulário válido, em que o `comentario.save()` só roda com o modo desligado.

A ordem das checagens (honeypot/time-trap → limite de taxa → receita → formulário) não
muda (spec 007, ADR-3; nota de manutenção do `specs/README.md`). O ramo do limite e o do
comentário vazio ficam como estão.

### Templates

- **`cadastro.html`**: entre o `h1` e o `<form>`, dentro de `{% if modo_demonstracao %}`:
  ```django
  <p class="mensagem mensagem--info aviso-demonstracao" role="note">
    <strong>Cadastro de demonstração:</strong> nenhuma conta é criada. Para ver o blog
    por dentro, <a href="{% url 'usuarios:entrar' %}">entre com a conta de demonstração</a>.
  </p>
  ```
- **`login.html`**: no mesmo lugar, um `<div class="mensagem mensagem--info
  aviso-demonstracao" role="note">` com `<strong>Conta de demonstração</strong>` e um
  `<dl class="credenciais">` com `Usuário` / `{{ conta_demonstracao.usuario }}` e `Senha` /
  `{{ conta_demonstracao.senha }}` (RF-04). Texto comum, selecionável; nenhum campo é
  preenchido sozinho.
- **`detalhe.html`**: dentro do `<form>` de comentário, logo depois do `carimbo_tempo` e
  antes da armadilha e do campo, `<p class="mensagem mensagem--info" role="note">` com
  "**Comentários de demonstração:** nada é publicado." (RF-06). A mensagem pós-envio já
  aparece dentro de `#comentarios` pelo `includes/mensagens.html` (spec 008, RF-05).

Os comentários novos nos templates seguem a regra do projeto (`{# #}` numa linha).

### CSS (`tokens.css` e `base.css`)

- **`--fonte-mono`** em `tokens.css`: `ui-monospace, "Cascadia Mono", Consolas, monospace`.
  Só fontes do sistema, nada baixado (a regra das fontes hospedadas segue valendo).
- **`.mensagem a { color: var(--cor-primaria-escura); }`**: o link da cor primária sobre o
  fundo de `.mensagem--info` (`--cor-borda`) fica abaixo de 4,5:1; o tom escuro passa nos
  dois temas. O `nucleo/test_tema_escuro.py` ganha o par `--cor-primaria-escura` ×
  `--cor-borda` com mínimo 4,5 (RNF-03).
- **`.aviso-demonstracao`**: `max-width: 420px`, `margin-inline: auto`, `text-align: left`.
  A caixa fica centrada na largura do formulário de acesso e o texto, de duas linhas, à
  esquerda (regra de alinhamento da spec 008: a caixa é curta e isolada; o texto dentro é
  leitura).
- **`.credenciais`**: `display: grid; grid-template-columns: auto 1fr;` com `gap` por token,
  `dt` em negrito e `dd` sem margem, em `--fonte-mono`.

Nenhuma cor nova: tudo por token existente.

### `docs/design-system.html`

Na seção "Mensagens", um exemplo de `.aviso-demonstracao` com `.credenciais`, com a
classe e o template de origem na legenda, como os outros exemplos.

### `.github/workflows/lighthouse.yml`

`MODO_DEMONSTRACAO: "True"` no `env` do passo que sobe o servidor: o Lighthouse audita as
páginas de login e cadastro como a instância pública as mostra, com o aviso e as
credenciais. O `semear_dados_demo` não depende do modo, e a página da receita auditada
é a anônima (sem formulário de comentário), então ela não muda.

### Documentação

- **`.env.example`**: `MODO_DEMONSTRACAO=False`, com o comentário do efeito (cadastro e
  comentário validam e não gravam; o login mostra a conta de demonstração) e a lembrança
  de rodar `criar_conta_demonstracao` (RNF-04).
- **`README.md` / `README.en.md`**: um parágrafo junto do `semear_dados_demo` sobre o modo e
  o comando, nos dois idiomas, na mesma posição (o `nucleo/test_readme_en.py` compara).
- **`CLAUDE.md`**: o comando em "Comandos comuns" e `blog_culinario/demonstracao.py` na
  árvore de arquitetura.
- **`specs/README.md`**: a linha da 009 no roadmap.

## Interfaces

Nenhuma URL nova; as três que mudam respondem como hoje com o modo desligado.

| URL | Método | Modo ligado |
|---|---|---|
| `/usuarios/cadastro/` | GET | 200 com o aviso |
| `/usuarios/cadastro/` | POST válido | 302 para `/usuarios/cadastro/`, mensagem `info`, nenhum `User` novo |
| `/usuarios/cadastro/` | POST inválido | 200 com os erros de campo (igual a hoje) |
| `/usuarios/entrar/` | GET | 200 com a caixa de credenciais |
| `/receitas/<slug>/` | GET autenticado | 200 com o aviso no formulário |
| `/receitas/<slug>/comentar/` | POST válido ou pego pelo honeypot | 302 para `#comentarios`, mensagem `info`, nenhum `Comentario` novo |

Linha de comando: `uv run python manage.py criar_conta_demonstracao` (sem argumentos).

## Interface

Decisão de projeto (2026-11-16): o aviso fixo fica **acima do formulário**, lido antes do
primeiro campo; uma nota abaixo do botão foi descartada porque o visitante só a leria
depois de preencher tudo. No login, a
caixa com "Conta de demonstração" e as credenciais em lista de definição; no comentário,
o aviso dentro do formulário, antes do campo; depois do envio, a mensagem volta em
`#comentarios` e o texto digitado não aparece na lista. A 1280 px o desenho é o mesmo:
os formulários de acesso já ficam numa coluna centrada de 420 px, e a seção de
comentários segue a largura do container.

## ADRs

### ADR-1 — O modo decide na view, depois da validação, no ponto em que grava

**Decisão.** `CadastroView.form_valid` e `ComentarioCreateView.post` consultam o modo
logo antes de gravar e respondem a mensagem em vez de chamar `save()`.
**Alternativas.** (a) Um middleware que bloqueia POST de cadastro e comentário. (b)
Sobrescrever `Comentario.save()` ou usar um signal `pre_save`. (c) Desligar as rotas.
**Porquê.** A validação continua inteira (RNF-02) e o visitante vê os erros de verdade; a
decisão fica visível onde quem estuda o código procura (a view que grava). (a) cortaria a
validação; (b) também afetaria o Admin e o `semear_dados_demo`; (c) tiraria a experiência
que a demo quer mostrar.
**Trade-off.** Duas views conhecem o modo; um formulário novo que grave dado de visitante
precisa lembrar de consultá-lo.

### ADR-2 — Link na mensagem por `format_html`, não por `extra_tags` nem texto fixo

**Decisão.** As mensagens pós-envio são `SafeString` montadas com `format_html` a partir
de constantes, e o `includes/mensagens.html` as mostra como estão.
**Alternativas.** (a) Mensagem sem link e um `extra_tags` que o template troca por um
parágrafo com link. (b) Mensagem só com texto e o link num parágrafo fixo da página.
**Porquê.** O texto inteiro fica num lugar só, e o armazenamento de mensagens do Django
(cookie e sessão) preserva a marca de texto seguro entre o POST e o GET. (a) espalharia
o texto entre Python e template; (b) mostraria o link mesmo sem envio.
**Trade-off.** Uma `SafeString` nunca pode interpolar dado do visitante; as duas funções
só usam constantes, e o `format_html` escaparia qualquer argumento mesmo assim.

### ADR-3 — Context processor em vez de contexto por view

**Decisão.** `contexto_demonstracao` entrega `modo_demonstracao` (e, ligado,
`conta_demonstracao`) a todo template.
**Alternativas.** (a) `get_context_data` no `CadastroView`, no `EntrarView` e no
`ReceitaDetailView`. (b) Uma template tag.
**Porquê.** Um lugar só para três templates, e um context processor próprio é um recurso
do Django que o projeto ainda não mostrava. (a) repetiria a mesma linha em três views.
**Trade-off.** Roda em toda renderização; o custo é ler uma setting.

### ADR-4 — Cadastro aceito redireciona de volta ao cadastro

**Decisão.** No modo ligado, o cadastro válido responde 302 para `/usuarios/cadastro/`
com a mensagem `info`.
**Alternativas.** (a) Renderizar a mesma página com o formulário preenchido. (b)
Redirecionar para a home, como o cadastro real.
**Porquê.** Post/redirect/get: o F5 não reenvia o formulário, as senhas somem da tela e a
mensagem aparece onde a pessoa estava, junto do aviso fixo que aponta o login. (b)
sugeriria que algo deu certo.
**Trade-off.** O nome de usuário digitado some junto; para quem só estava conferindo a
validação, não faz falta.

### ADR-5 — Credenciais no código, não em variável de ambiente

**Decisão.** `USUARIO_DEMONSTRACAO` e `SENHA_DEMONSTRACAO` são constantes de
`blog_culinario/demonstracao.py`, usadas pelo comando e pelo context processor.
**Alternativas.** (a) Variáveis `CONTA_DEMONSTRACAO_USUARIO` e `..._SENHA`. (b) Ler as
credenciais do banco.
**Porquê.** A senha é pública de propósito (aparece na tela); uma variável daria a falsa
impressão de segredo e seria mais uma configuração para esquecer. Uma fonte só garante
que a tela mostra a senha que o comando grava.
**Trade-off.** Trocar a senha exige mudar o código e reimplantar.

### ADR-6 — O comando roda com o modo desligado, com aviso

**Decisão.** `criar_conta_demonstracao` cria ou atualiza a conta em qualquer ambiente e,
com o modo desligado, avisa que ela publica comentários de verdade.
**Alternativas.** (a) Recusar com o modo desligado, como o `semear_dados_demo` recusa
`DEBUG=False`.
**Porquê.** Quem clona pode querer a mesma conta localmente para testar o modo, e o banco
da instância pública pode receber a conta antes de a variável ser ligada. O aviso cobre o
risco de esquecer a variável.
**Trade-off.** Uma instância com a conta e sem o modo publica o que o visitante comentar;
o aviso do comando é a proteção.

## Impacto no código existente

- **Modo desligado (padrão):** nenhum comportamento muda; os testes atuais de cadastro,
  login e comentário seguem passando sem alteração.
- **Lighthouse CI:** login e cadastro passam a ser auditados com o aviso, que é o que a
  instância pública mostra. O peso da página cresce algumas centenas de bytes; os limites
  de `.github/lighthouse/` não mudam.
- **Mensagem `info` com link:** primeira mensagem do projeto com HTML; `includes/
  mensagens.html` não muda (o `{{ message }}` já respeita `SafeString`).
- **Sem migration, sem dependência nova** (RNF-01).

## Estratégia de testes

Testes de integração com o `Client` do Django e `override_settings(MODO_DEMONSTRACAO=...)`,
num arquivo por app:

- **`usuarios/test_modo_demonstracao.py`**: padrão desligado (`settings.MODO_DEMONSTRACAO`
  é `False` sem a variável, e o contexto não traz credenciais); aviso e credenciais só com
  o modo ligado; cadastro inválido com os mesmos erros; cadastro válido sem `User` novo,
  com a sessão anônima, redirect para o cadastro e o `<a href="https://github.com/...">`
  no HTML seguinte (RF-01 a RF-04, RNF-03); login da conta criada pelo comando; o comando
  com `call_command` criando sem staff, restaurando senha e flags numa segunda execução
  sem duplicar, e avisando com o modo desligado (RF-05, ADR-6).
- **`receitas/test_modo_demonstracao.py`**: aviso no formulário só com o modo ligado e
  usuário autenticado; envio válido e envio pego pelo honeypot sem `Comentario` novo e com
  a mensagem do modo; vazio e limite de taxa como hoje; modo desligado publicando (RF-06).
  O carimbo de tempo válido sai do helper que os testes da spec 007 já usam, e o cache do
  limite é limpo entre os testes como nos testes da spec 006.
- **`nucleo/test_tema_escuro.py`**: o par `--cor-primaria-escura` × `--cor-borda` com
  mínimo 4,5 nos dois temas (RNF-03).

Nada é mockado além das settings. O portão completo (`ruff` → `black` → `mypy` →
`pytest`) fecha cada etapa.

## Desvios

1. **Mensagens das páginas de acesso na coluna do formulário** (RF-03, RNF-03). Na
   conferência a 1280 px, a mensagem do cadastro recusado saía do bloco `mensagens` do
   `base.html`, no topo à esquerda e com 618 px, longe do formulário centrado de 420 px.
   `cadastro.html` e `login.html` passaram a esvaziar o bloco e incluir
   `includes/mensagens.html` logo depois do `h1`, e `.pagina-formulario .mensagens` põe a
   mensagem na largura do formulário, com o texto à esquerda (regra de alinhamento da spec
   008). Vale para toda mensagem dessas duas páginas, inclusive a do limite de tentativas
   de login (spec 006).

## Notas de implementação

- **Onde a lógica caiu:** `blog_culinario/demonstracao.py` (constantes, as duas
  mensagens, o context processor); o modo é consultado em dois pontos de gravação,
  `CadastroView.form_valid` e `ComentarioCreateView.post`, e no método
  `_confirmar_envio`, que o ramo do honeypot e o do formulário válido compartilham.
- **Testes:** de 180 para 202 (22 novos em `usuarios/test_modo_demonstracao.py` e
  `receitas/test_modo_demonstracao.py`, mais o par de contraste do link no
  `nucleo/test_tema_escuro.py`). Os testes que já existiam passaram sem alteração com o
  modo desligado.
- **Conferência no navegador** (Chrome, 390 e 1280 px, tema claro e escuro, modo ligado,
  banco temporário com `semear_dados_demo` e `criar_conta_demonstracao`): o aviso fixo e o
  formulário de acesso têm a mesma posição e largura (358 px a 390, 420 px a 1280), sem
  rolagem lateral; o login com `visitante` leva de volta à receita do `?next=`; depois do
  envio, o comentário não aparece na lista e a mensagem traz o `<a>` do repositório. A cor
  do link na mensagem medida na tela foi `rgb(156, 54, 11)` sobre `rgb(232, 220, 200)` no
  claro e `rgb(245, 167, 130)` sobre `rgb(74, 61, 51)` no escuro.
