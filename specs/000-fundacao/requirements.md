---
feature: Fundação do projeto (bootstrap)
status: concluído
data: 2026-09-12
relacionado: []
origem: engenharia reversa
---

# 000 — Fundação do projeto (bootstrap)

## Contexto e problema

Antes de existir qualquer spec de feature, o projeto passou por uma fase de
planejamento para decidir arquitetura, stack e convenções, e por um
bootstrap que deixou o repositório num estado "pronto para receber
specs": Django rodando localmente, design system próprio validado
visualmente, repositório GitHub configurado com os serviços gratuitos
padrão do mantenedor, e toda a documentação de projeto (README, CONTRIBUTING,
CLAUDE.md, `docs/stack.md`) no lugar. Esta spec registra retroativamente
essa fase — por decisão do mantenedor, que trata as specs também como o
histórico de como o projeto foi construído, desde o início.

Diferente das specs seguintes, aqui não há um "problema de domínio" a
resolver — o objetivo era puramente estrutural: montar o alicerce sobre o
qual as specs 001 em diante iriam construir.

## Objetivos

- Projeto Django funcional localmente, sem exigir configuração manual de
  quem clona o repositório.
- Design system próprio (HTML + CSS puro, sem framework de frontend),
  validado visualmente antes de qualquer feature de domínio existir.
- Repositório GitHub público, com os serviços gratuitos padrão do
  mantenedor ativados por padrão.
- Documentação de projeto completa (README educacional, CONTRIBUTING,
  CLAUDE.md, LICENSE, `docs/stack.md`).
- CI rodando o mesmo portão de qualidade usado localmente.
- Terreno pronto para o fluxo spec-driven (`specs/`) começar na spec 001.

## Não-objetivos

- Qualquer modelo, view ou funcionalidade do domínio de receitas — isso é
  escopo da spec 001 em diante.
- `specs/README.md` (a metodologia de spec-driven development) — foi
  criado junto com a primeira spec de feature (001), não faz parte desta
  fundação.
- Deploy em produção — planejado para o PythonAnywhere, mas só quando o
  blog estiver funcionalmente pronto (decisão registrada nesta mesma
  fase, não executada aqui).

## Personas

- Como **mantenedor**, quero um ponto de partida sólido e já com as boas
  práticas do projeto (uv, Conventional Commits, Dependabot, CLAUDE.md) antes
  de começar a construir features.
- Como **um estudante clonando o repositório** (o público-alvo do projeto),
  quero rodar `uv sync && python manage.py runserver` e ver o site
  funcionando, sem precisar decifrar configuração.

## Requisitos funcionais

### RF-01 — Decisões de arquitetura registradas antes do código

- **Given** o pedido inicial de criar um blog culinário educacional
  **When** o trabalho começa
  **Then** uma fase de planejamento formal precede qualquer código: idioma
  do projeto, abordagem de frontend, banco de dados e nome do
  repositório são decididos explicitamente com o mantenedor antes de
  escrever a primeira linha.

### RF-02 — Projeto Django roda localmente sem configuração adicional

- **Given** alguém acabou de clonar o repositório
  **When** roda `uv sync`, `python manage.py migrate` e
  `python manage.py runserver`
  **Then** o site sobe em `http://127.0.0.1:8000/` sem exigir nenhuma
  variável de ambiente (defaults seguros em `settings/dev.py`).

### RF-03 — Configuração separada por ambiente

- **Given** o projeto precisa se comportar diferente em desenvolvimento e
  produção
  **When** o `DJANGO_SETTINGS_MODULE` aponta para `dev` ou `prod`
  **Then** cada um herda de `settings/base.py` e sobrescreve só o que é
  específico do ambiente (`DEBUG`, `ALLOWED_HOSTS`, hardening HTTPS).

### RF-04 — Design system próprio, validado visualmente

- **Given** o objetivo de um frontend "rico e bonito", construído sem
  framework
  **When** a home renderiza
  **Then** exibe a paleta, tipografia (Fraunces/Inter) e componentes
  (navbar, hero, cartão de receita, rodapé) definidos em
  `static/css/tokens.css`/`base.css`, responsivos em mobile — conferido
  via screenshot antes de qualquer feature de domínio existir.

### RF-05 — Repositório GitHub com os serviços gratuitos padrão

- **Given** o repositório é criado no GitHub
  **When** a criação é confirmada
  **Then** já nasce com visibilidade pública, delete-branch-on-merge,
  Dependabot (`security updates` + `version updates` via
  `dependabot.yml`), secret scanning e secret scanning push protection
  ativados — sem precisar de um passo manual depois.

### RF-06 — CI espelha o portão de qualidade local

- **Given** um push ou pull request no repositório
  **When** o workflow do GitHub Actions roda
  **Then** executa `ruff check`, `black --check`, `mypy` e `pytest`, na
  mesma ordem usada localmente.

### RF-07 — Documentação de projeto completa

- **Given** um visitante abre o repositório pela primeira vez
  **When** lê o `README.md`
  **Then** encontra o objetivo educacional do projeto, a stack, como
  rodar, e atividades sugeridas para praticar (modelo "educacional" de
  README adotado pelo projeto) — com `CONTRIBUTING.md`, `LICENSE` (MIT) e
  `CLAUDE.md` (convenções para quem/o que edita o repo) como
  complementos.

### RF-08 — Stack documentada com o porquê de cada escolha

- **Given** as dependências de runtime e desenvolvimento já instaladas
  **When** alguém abre `docs/stack.md`
  **Then** encontra, por peça da stack, o que ela faz, por que foi
  escolhida contra a alternativa considerada, e o que estudar primeiro —
  incluindo uma seção explícita do que ficou deliberadamente fora
  (PostgreSQL, Tailwind, React, Docker, etc.).

## Requisitos não-funcionais

### RNF-01 — Idioma português consistente

Nomes de classes/funções/variáveis, commits, comentários técnicos e toda a
documentação de projeto em português — projeto classificado como
"Educacional PT-BR", exceto onde o próprio
Django/pytest impõe nomes em inglês.

### RNF-02 — Zero framework de frontend

HTML + CSS puro (custom properties para tokens de design) + JavaScript
vanilla mínimo — sem Node, sem build step — para manter o projeto 100%
focado em ensinar Django.

### RNF-03 — Primeiro commit direto na main é a exceção, não a regra

Por o repositório nascer vazio (unborn branch, sem histórico a proteger), o
commit de bootstrap foi direto na `main` — decisão explícita, registrada
como exceção pontual; toda spec a partir da 001 segue o fluxo normal de
branch + PR.

## Perguntas em aberto

Nenhuma — esta spec documenta decisões já tomadas e executadas; não há
fase de concepção em aberto para uma fundação que já existe.

## Testes

Sem suíte automatizada própria (não há lógica de domínio nesta fase). A
verificação foi:
- `python manage.py check` sem warnings.
- Portão de qualidade (`ruff`, `black`, `mypy`) verde.
- Verificação visual manual (screenshots desktop + mobile da home) antes
  de considerar o design system pronto.
