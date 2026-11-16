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

# 009 — Modo demonstração — Tasks

## Etapa 1 — Setting, módulo e context processor

- [x] `blog_culinario/settings/base.py`: `MODO_DEMONSTRACAO = env.bool("MODO_DEMONSTRACAO", default=False)`, com comentário do efeito. — RF-01
- [x] `blog_culinario/demonstracao.py` (novo): `USUARIO_DEMONSTRACAO`, `SENHA_DEMONSTRACAO`, `URL_REPOSITORIO`, `modo_demonstracao_ligado()` (lê a setting na chamada), `mensagem_cadastro()` e `mensagem_comentario()` com `format_html` e link `target="_blank" rel="noopener"`. — RF-03, RF-06, ADR-2, ADR-5
- [x] `blog_culinario/demonstracao.py`: `contexto_demonstracao(request)` devolve `modo_demonstracao` e, só com o modo ligado, `conta_demonstracao`. — RF-04, ADR-3
- [x] `blog_culinario/settings/base.py`: `"blog_culinario.demonstracao.contexto_demonstracao"` no fim de `context_processors`. — ADR-3
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 180 passed; ruff/black/mypy verdes

## Etapa 2 — Views e comando

- [x] `usuarios/views.py`: `CadastroView.form_valid` consulta o modo antes do `form.save()`; ligado, `messages.info(mensagem_cadastro())` e redirect para `usuarios:cadastro`. Docstrings do módulo e do método citam a spec 009. — RF-03, RNF-02, ADR-1, ADR-4
- [x] `receitas/views.py`: método `_confirmar_envio(request)` (mensagem `info` do modo ou `success` "Comentário publicado!"); o ramo do honeypot e o do formulário válido passam a usá-lo, e o `comentario.save()` só roda com o modo desligado. Ordem das checagens intacta; docstring do `post()` atualizada. — RF-06, RNF-02, ADR-1
- [x] `usuarios/management/__init__.py`, `usuarios/management/commands/__init__.py` e `usuarios/management/commands/criar_conta_demonstracao.py` (novos): `get_or_create` do `visitante`, senha, `is_active=True`, `is_staff=False`, `is_superuser=False`; "criada"/"atualizada" no `stdout` e aviso `WARNING` com o modo desligado. — RF-05, ADR-5, ADR-6
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 180 passed; ruff/black/mypy e `manage.py check` verdes

## Etapa 3 — Templates, CSS e catálogo

- [x] `usuarios/templates/usuarios/cadastro.html`: `<p class="mensagem mensagem--info aviso-demonstracao" role="note">` entre o `h1` e o `<form>`, dentro de `{% if modo_demonstracao %}`, com o link para `usuarios:entrar`. — RF-02
- [x] `usuarios/templates/usuarios/login.html`: caixa `aviso-demonstracao` com "Conta de demonstração" e `<dl class="credenciais">` lendo `conta_demonstracao`. — RF-04
- [x] `receitas/templates/receitas/detalhe.html`: aviso "Comentários de demonstração: nada é publicado." dentro do `<form>`, depois do `carimbo_tempo`. — RF-06
- [x] `static/css/tokens.css`: `--fonte-mono` (só fontes do sistema). — RNF-03
- [x] `static/css/base.css`, seção de mensagens: `.mensagem a` em `--cor-primaria-escura`, `.aviso-demonstracao` (420 px, centrada, texto à esquerda) e `.credenciais` (grid de duas colunas, `dd` em `--fonte-mono`), só com tokens. — RNF-03
- [x] `docs/design-system.html`: exemplo do aviso com as credenciais na seção "Mensagens". — RNF-03
- [x] Conferência no navegador a 390 e 1280 px, tema claro e escuro, com o modo ligado: cadastro, login, receita logado como `visitante`, e as mensagens depois de cada envio; comparar com a interface descrita no `design.md`. — RF-02, RF-04, RF-06; aviso e formulário com a mesma posição e largura (358 px a 390, 420 px a 1280), sem rolagem lateral; a mensagem pós-cadastro saía no topo à esquerda (desvio 1 do `design.md`)
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 180 passed; ruff/black/mypy verdes

## Etapa 4 — Testes

- [x] `usuarios/test_modo_demonstracao.py` (novo): padrão desligado; aviso e credenciais só com o modo ligado; cadastro inválido com os erros de hoje; cadastro válido sem `User` novo, sessão anônima, redirect e `<a>` do GitHub no HTML seguinte; login da conta; comando criando, restaurando sem duplicar e avisando com o modo desligado. — RF-01, RF-02, RF-03, RF-04, RF-05, RF-07, RNF-03, ADR-6
- [x] `receitas/test_modo_demonstracao.py` (novo): aviso só com o modo ligado e usuário autenticado; envio válido e honeypot sem `Comentario` novo e com a mensagem do modo; vazio e limite como hoje; modo desligado publicando. Reaproveita o carimbo válido e a limpeza do cache dos testes das specs 006 e 007. — RF-06, RF-07
- [x] `nucleo/test_tema_escuro.py`: par `--cor-primaria-escura` × `--cor-borda`, mínimo 4,5, nos dois temas. — RNF-03
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 202 passed (22 novos); ruff/black/mypy verdes

## Etapa 5 — CI e documentação

- [x] `.github/workflows/lighthouse.yml`: `MODO_DEMONSTRACAO: "True"` no passo que sobe o servidor, com comentário do motivo. — RF-02, RF-04
- [x] `.env.example`: `MODO_DEMONSTRACAO=False` com o efeito e o comando `criar_conta_demonstracao`. — RNF-04
- [x] `README.md` e `README.en.md`: parágrafo sobre o modo e o comando junto do `semear_dados_demo`, na mesma posição nos dois. — RNF-04
- [x] `CLAUDE.md`: comando em "Comandos comuns" e `blog_culinario/demonstracao.py` na arquitetura. — RNF-04
- [x] `specs/README.md`: linha da 009 no roadmap; `status` concluído nos três arquivos da spec; `## Desvios` e `## Notas de implementação` no `design.md`. — RF-07
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 202 passed; ruff/black/mypy verdes; rastreabilidade conferida
