---
feature: Honeypot e time-trap no formulário de comentário
status: concluído
date: 2026-09-12
related:
  - 005-comentarios/requirements.md
  - 006-limitacao-de-taxa/requirements.md
origin: concepcao
---

# 007 — Honeypot e time-trap no formulário de comentário — Tasks

## Etapa 1 — Funções e campos em `FormularioComentario`

- [x] `receitas/forms.py`: `gerar_carimbo_de_tempo() -> str` (assina `time.time()` via `django.core.signing.dumps`, salt próprio da spec 007). — RF-02, RNF-01
- [x] `receitas/forms.py`: `eh_envio_suspeito_de_bot(dados: QueryDict) -> bool` (honeypot não-vazio, ou carimbo ausente/adulterado/recente demais). — RF-01, RF-02
- [x] `receitas/forms.py`: `FormularioComentario` ganha `endereco_web` (`CharField(required=False, label="")`, widget com `tabindex="-1"` + `autocomplete="off"`) e `carimbo_tempo` (`CharField(required=False, widget=HiddenInput())`). — RF-01, RNF-02
- [x] Portão de qualidade parcial: `ruff check` + `black --check` + `mypy` verdes.

## Etapa 2 — Aplicar nas views

- [x] `receitas/views.py`: `ReceitaDetailView.get_context_data()` instancia `FormularioComentario(initial={"carimbo_tempo": gerar_carimbo_de_tempo()})`. — RF-02
- [x] `receitas/views.py`: `ComentarioCreateView.post()` chama `eh_envio_suspeito_de_bot(request.POST)` antes de `limite_excedido()`; se suspeito, mensagem de sucesso + redirect sem salvar (ADR-3, ADR-4). — RF-01, RF-02, RF-03, RNF-03
- [x] Portão de qualidade parcial: verdes (`manage.py check` também).

## Etapa 3 — Template e CSS

- [x] `receitas/templates/receitas/detalhe.html`: `{{ formulario_comentario.carimbo_tempo }}` + `<div class="campo-armadilha" aria-hidden="true">` envolvendo o label e `{{ formulario_comentario.endereco_web }}`. — RF-01, RF-02
- [x] `static/css/base.css`: classe `.campo-armadilha` (posicionamento fora da tela, não `display: none`/`visibility: hidden`). — ADR-1
- [x] Verificação visual manual (Playwright): formulário renderiza normalmente, campo-armadilha invisível e sem afetar o layout (screenshot conferido).
- [x] Portão de qualidade parcial: verdes.

### Nota da verificação visual

`page.query_selector(...).is_visible()` do Playwright acusou o honeypot
como "visível" — mas isso é só a definição de visibilidade do Playwright
(`display`/`visibility`/`opacity`, bounding box não-vazio), que não
considera elemento posicionado fora da tela (`left: -9999px`) como
oculto. O screenshot confirma que nenhum campo extra aparece — a página
renderiza igual à versão sem honeypot.

## Etapa 4 — Testes

- [x] `receitas/tests.py`: honeypot preenchido não cria comentário, mas resposta é indistinguível de sucesso (mesmo redirect/mensagem). — RF-01, RF-03
- [x] `receitas/tests.py`: carimbo recente demais (tempo atual) bloqueia; carimbo ausente ou adulterado é tratado como suspeito. — RF-02
- [x] `receitas/tests.py`: carimbo gerado no passado (`time.time() - 5`) + honeypot vazio cria o comentário normalmente (sem falso positivo). — RF-03
- [x] `receitas/tests.py`: um envio bloqueado por honeypot/time-trap não consome o contador de limite de taxa da spec 006 (uma chamada real subsequente ainda está dentro do limite de 5/minuto). — RNF-03
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **67 passed**; `manage.py check` sem issues.

### Correção feita durante a implementação

Os testes de comentário das specs 005/006 já existentes POSTavam sem
`carimbo_tempo` -- com a checagem antibot rodando primeiro, isso os teria
quebrado silenciosamente (o envio "fingiria sucesso" sem criar o
comentário, mascarando o que cada teste realmente queria verificar).
Corrigido acrescentando `"carimbo_tempo": _carimbo_valido()` aos POSTs que
esperam criação real: `test_post_valido_cria_comentario_e_redireciona`,
`test_post_com_texto_vazio_nao_cria_comentario`,
`test_bloqueia_a_partir_do_sexto_comentario_no_mesmo_ip` e
`test_dois_ips_nao_compartilham_o_limite_de_comentarios`.
