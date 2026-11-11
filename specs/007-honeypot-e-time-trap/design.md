---
feature: Honeypot e time-trap no formulário de comentário
status: concluído
date: 2026-09-12
related:
  - 005-comentarios/requirements.md
  - 006-limitacao-de-taxa/requirements.md
origin: concepcao
---

# 007 — Honeypot e time-trap no formulário de comentário — design

## Visão geral da abordagem

Dois campos extras, não-modelo, em `FormularioComentario`: `endereco_web`
(honeypot, oculto por CSS) e `carimbo_tempo` (hidden, timestamp assinado
gerado no GET). `ComentarioCreateView.post()` lê os dois diretamente de
`request.POST` **antes** de qualquer outra checagem — se o honeypot veio
preenchido ou o tempo decorrido é curto demais, a view finge sucesso sem
tocar no banco, no limite de taxa da spec 006, ou em qualquer mensagem de
erro.

## Componentes

### `receitas/forms.py` (funções novas + campos novos em `FormularioComentario`)

```python
def gerar_carimbo_de_tempo() -> str
def eh_envio_suspeito_de_bot(dados: QueryDict) -> bool
```

- `gerar_carimbo_de_tempo()` — assina o instante atual (`time.time()`) via
  `django.core.signing.dumps`, com um `salt` próprio da spec 007. Chamada
  pela view no GET, como `initial` do campo `carimbo_tempo`.
- `eh_envio_suspeito_de_bot(dados)` — recebe `request.POST` cru (não o
  form validado — deliberado, ver ADR-3) e retorna `True` se:
  - `endereco_web` veio não-vazio (RF-01), ou
  - `carimbo_tempo` está ausente/adulterado (`signing.BadSignature`) ou o
    tempo decorrido desde a assinatura é menor que `_TEMPO_MINIMO_SEGUNDOS`
    (RF-02).
- `FormularioComentario` ganha `endereco_web` (`CharField(required=False,
  label="")`, widget com `tabindex="-1"` e `autocomplete="off"` — RNF-02) e
  `carimbo_tempo` (`CharField(required=False, widget=HiddenInput())`) —
  nenhum dos dois é campo do modelo `Comentario`, então `form.save()`
  continua ignorando-os automaticamente.

### `receitas/views.py::ReceitaDetailView`

`get_context_data()` passa a instanciar o formulário com
`initial={"carimbo_tempo": gerar_carimbo_de_tempo()}` — o carimbo nasce no
momento em que a página é servida, não em que o comentário é enviado.

### `receitas/views.py::ComentarioCreateView`

`post()` ganha uma checagem no topo, antes do limite de taxa da spec 006:

```python
if eh_envio_suspeito_de_bot(request.POST):
    messages.success(request, "Comentário publicado!")
    return redirect(url_retorno)
```

O restante do método (limite de taxa, busca da receita, validação e save)
não muda.

### `receitas/templates/receitas/detalhe.html`

O formulário ganha `{{ formulario_comentario.carimbo_tempo }}` (hidden) e
um `<div class="campo-armadilha" aria-hidden="true">` envolvendo o label +
`{{ formulario_comentario.endereco_web }}`.

### `static/css/base.css`

Classe nova `.campo-armadilha`: posiciona o campo fora da tela
(`position: absolute; left: -9999px`) sem usar `display: none`/
`visibility: hidden` — algumas ferramentas de scraping simples ignoram
campos explicitamente invisíveis via essas duas propriedades, mas não
verificam posição.

## Modelo de dados

Nenhum. `endereco_web` e `carimbo_tempo` nunca chegam ao banco — existem
só na camada de formulário/HTTP.

## Interfaces

Nenhuma URL nova. Comportamento adicional nos endpoints já existentes:

| Método | URL | Mudança |
|---|---|---|
| GET | `/receitas/<slug>/` | Formulário de comentário ganha 2 campos ocultos (honeypot + carimbo) |
| POST | `/receitas/<slug>/comentar/` | Honeypot/time-trap checados antes do limite de taxa; se disparado, finge sucesso sem salvar |

## ADRs

### ADR-1 — Honeypot como campo de texto real oculto por CSS, não `type="hidden"`

**Decisão.** `endereco_web` é um `<input type="text">` normal, escondido
via `position: absolute; left: -9999px` no CSS.
**Alternativas.** `forms.HiddenInput()` (`type="hidden"`).
**Porquê.** Bots feitos especificamente para reconhecer honeypots pulam
campos `type="hidden"` por padrão — um campo de texto "normal" escondido
só visualmente é mais convincente para o bot simples que este projeto
mira (RF-01).
**Trade-off.** Exige disciplina de acessibilidade (`tabindex="-1"`,
`autocomplete="off"`, `aria-hidden="true"` no contêiner) para não confundir
navegação por teclado ou leitor de tela — tratado no RNF-02.

### ADR-2 — Time-trap com carimbo assinado no próprio formulário, sem estado no servidor

**Decisão.** `django.core.signing.dumps`/`loads` num campo hidden do
formulário, carregando o timestamp de quando a página foi servida.
**Alternativas.** Guardar o horário de renderização no cache (mesma
técnica da spec 006), com chave por sessão.
**Porquê.** Um valor assinado viaja com o próprio POST — sem exigir
armazenamento novo no servidor, sem se preocupar com múltiplas abas da
mesma receita abertas ao mesmo tempo (cada renderização carrega seu
próprio carimbo, independente).
**Trade-off.** Sem limite máximo de idade do carimbo: uma aba deixada
aberta por horas ainda passa no time-trap quando o comentário for enviado
(aceitável — o objetivo é só pegar envio *rápido* demais, não expirar a
sessão de comentário). Um bot que capturasse um carimbo antigo de uma
página salva e o reenviasse rapidamente também passaria — cenário fora do
threat model de um bot simples que preenche formulários ao vivo.

### ADR-3 — Checagem lê `request.POST` cru, não o form validado

**Decisão.** `eh_envio_suspeito_de_bot()` recebe o `QueryDict` de
`request.POST` diretamente, roda **antes** de instanciar
`FormularioComentario` para validação, e roda antes do `limite_excedido()`
da spec 006.
**Alternativas.** Checar via `form.cleaned_data` depois de
`form.is_valid()`.
**Porquê.** RF-01 exige rejeitar honeypot preenchido *independente* do
conteúdo de `texto` (mesmo um `texto` inválido/vazio) — amarrar a checagem
à validade do form criaria uma brecha. Rodar antes do limite de taxa
também cumpre RNF-03: um bot filtrado pelo honeypot/time-trap não consome
o orçamento de 5 comentários/minuto por IP, preservando esse orçamento
para humanos genuínos atrás do mesmo IP.
**Trade-off.** Duas fontes de verdade para os mesmos dados brutos
(`request.POST` aqui, o form mais abaixo) — aceitável porque
`endereco_web`/`carimbo_tempo` nunca participam da validação de domínio
do `texto`.

### ADR-4 — Falha silenciosa (finge sucesso) em vez de mensagem de erro

**Decisão.** Honeypot ou time-trap disparado → mesma mensagem de sucesso
("Comentário publicado!") e mesmo redirect que um envio real, sem
persistir nada.
**Alternativas.** Mensagem de erro genérica.
**Porquê.** RF-01/RNF-03 — não dar ao bot nenhum sinal de que foi
detectado, para ele não adaptar o próximo envio.
**Trade-off.** Se um humano disparar por engano (falha de acessibilidade
não prevista), ele não recebe explicação nenhuma do "comentário sumido" —
mitigado pelo RNF-02 (a11y correta) e pelo tempo mínimo de 2s ser folgado
o bastante para não pegar uso normal.

## Impacto no código existente

- `receitas/forms.py` — `gerar_carimbo_de_tempo()`, `eh_envio_suspeito_de_bot()`, e os 2 campos novos em `FormularioComentario`.
- `receitas/views.py` — `ReceitaDetailView.get_context_data()` passa `initial`; `ComentarioCreateView.post()` ganha a checagem no topo.
- `receitas/templates/receitas/detalhe.html` — 2 campos ocultos no formulário.
- `static/css/base.css` — classe `.campo-armadilha`.

## Estratégia de testes

- `receitas/tests.py`:
  - Honeypot preenchido → comentário não é criado, mas a resposta segue o
    mesmo redirect/mensagem de um envio bem-sucedido.
  - Carimbo de tempo recente demais (gerado com `time.time()` atual) →
    bloqueado da mesma forma.
  - Carimbo ausente ou adulterado (string arbitrária no lugar do valor
    assinado) → tratado como suspeito.
  - Carimbo gerado com timestamp já no passado (`time.time() - 5`, sem
    precisar de `sleep` real no teste) + honeypot vazio → comentário é
    criado normalmente.
  - Um envio bloqueado por honeypot/time-trap não consome o contador de
    limite de taxa da spec 006 (chamada subsequente ainda dentro do
    limite de 5/minuto).
