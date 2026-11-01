---
feature: Fundação do projeto (bootstrap)
status: concluído
data: 2026-09-12
relacionado: []
origem: engenharia reversa
---

# 000 — Fundação do projeto (bootstrap) — design

## Visão geral da abordagem

Uma fase de planejamento formal precedeu qualquer código:
arquitetura, stack e convenções foram decididas e escritas num plano antes
da primeira linha. A execução seguiu o próprio plano, na ordem: repositório
GitHub → projeto Django (uv, apps, settings) → design system → templates
institucionais → documentação de projeto → verificação → commit único
direto na `main`.

## Layout de módulos (como o repositório nasceu)

```
blog-culinario/
├── manage.py
├── blog_culinario/
│   ├── settings/
│   │   ├── base.py      # comum a todo ambiente
│   │   ├── dev.py        # default do manage.py
│   │   └── prod.py       # hardening HTTPS, ALLOWED_HOSTS obrigatório
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── nucleo/                # home institucional (única view real desta fase)
├── receitas/               # esqueleto (startapp puro, sem models ainda)
├── usuarios/                # esqueleto (idem)
├── templates/
│   ├── base.html
│   └── includes/navbar.html, rodape.html
├── static/
│   ├── css/tokens.css      # paleta, tipografia, espaçamento
│   ├── css/base.css         # reset, layout, componentes, responsivo
│   └── js/interacoes.js      # menu mobile, vanilla
├── .github/
│   ├── dependabot.yml
│   └── workflows/ci.yml
├── docs/stack.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── CLAUDE.md
└── LICENSE
```

## Componentes

### Fase de planejamento

Antes do código, idioma do código, abordagem de frontend, banco de dados e
nome do repositório foram decididos explicitamente com o mantenedor. O plano
resultante foi aprovado antes de qualquer comando `uv`/`django-admin`.

### `blog_culinario/settings/` (pacote, não um arquivo só)

`base.py` concentra tudo que não muda entre ambientes (apps, middleware,
templates, validação de senha, i18n, estáticos/mídia). `dev.py` sobrescreve
`DEBUG`/`ALLOWED_HOSTS` para uso local sem configuração. `prod.py` exige
`DJANGO_ALLOWED_HOSTS` (sem default) e liga hardening HTTPS
(`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, HSTS).

### Apps por domínio (`nucleo`, `receitas`, `usuarios`)

Criados via `startapp`, mas só `nucleo` ganhou conteúdo real nesta fase
(`views.home`, `urls.py`, o template da home) — `receitas` e `usuarios`
ficaram como esqueleto de propósito, esperando as specs 001 e 004.

### Design system (`static/css/tokens.css` + `base.css` + `interacoes.js`)

Paleta terracota/creme/verde sálvia (identidade "culinária"), tipografia
Fraunces (títulos) + Inter (corpo) via Google Fonts, espaçamento/raio/sombra
como custom properties. `base.css` implementa reset mínimo, layout
(`.container`, `.grade-receitas`), navbar sticky com menu mobile
(`interacoes.js` alterna a classe via JS vanilla), hero, cartão de receita
(componente reaproveitado pelas specs seguintes), botões e rodapé —
totalmente responsivo, sem media query além do breakpoint mobile único.

### Documentação de projeto

`README.md` no modelo "educacional" (objetivo, guia de implementação,
tecnologias, como rodar, atividades para praticar).
`CONTRIBUTING.md` convida contribuição enquadrando o repo como laboratório
de boas práticas. `CLAUDE.md` resume visão geral, comandos, arquitetura e
convenções (o projeto já nasceu sabendo que teria `specs/` e `docs/`, então
aponta para eles em vez de duplicá-los). `docs/stack.md` documenta cada peça
da stack com o porquê da escolha e o que estudar.

## Modelo de dados

Nenhum — a fundação não modela domínio (isso começa na spec 001).

## Interfaces

| Método | URL | View | Nome |
|---|---|---|---|
| GET | `/` | `nucleo.views.home` | `nucleo:home` |
| GET | `/admin/` | Django admin | — |
| GET | `/static/...` | WhiteNoise (prod) / Django (dev) | — |
| GET | `/media/...` | Django (dev, `DEBUG=True` apenas) | — |

## ADRs

### ADR-1 — Nome do repositório com a tecnologia na frente

**Decisão.** `django-blog-culinario` (não `blog-culinario-django` nem só
`blog-culinario`).
**Alternativas.** Nome sem prefixo de tecnologia; tecnologia como sufixo.
**Porquê.** Convenção de nomes do mantenedor: nome da tecnologia primeiro
(correção feita durante o planejamento).
**Trade-off.** Nenhum relevante.

### ADR-2 — SQLite como banco, mesmo sabendo do deploy no PythonAnywhere

**Decisão.** SQLite em todos os ambientes, inclusive produção.
**Alternativas.** PostgreSQL (mais realista para "produção de verdade").
**Porquê.** Zero configuração para quem clona o repo para estudar, e é o
banco suportado sem custo extra no plano gratuito do PythonAnywhere — as
duas motivações apontam pra mesma escolha.
**Trade-off.** Não ensina a operar um banco cliente-servidor; aceitável
dado que o foco pedagógico é Django, não administração de banco de dados.

### ADR-3 — Frontend construído do zero, sem V0 ou framework

**Decisão.** HTML + CSS puro com design system próprio, pesquisado e
construído do zero, em vez de gerar via V0 da Vercel ou adotar
Tailwind/Bootstrap.
**Alternativas.** V0 (design pronto, mas fora do fluxo 100% Django);
Tailwind (produtividade, mas esconde a construção de um design system do
zero, que é parte do valor didático).
**Porquê.** Decisão do mantenedor: qualidade visual de estúdio, mas
sem dependência externa ao ecossistema Django/Python.
**Trade-off.** Mais trabalho manual de CSS do que um gerador ou framework
utilitário resolveriam sozinhos.

### ADR-4 — Primeiro commit direto na `main`

**Decisão.** O commit de bootstrap foi direto na `main`, não numa branch
com PR.
**Alternativas.** Seguir o fluxo normal de branch + PR desde o primeiro
commit.
**Porquê.** Repositório recém-criado, sem nenhum histórico ou colaboração
a proteger (unborn branch) — não havia o que uma revisão de PR
protegeria. A partir do segundo commit (spec 001 em diante), o fluxo
normal passou a valer sem exceção.
**Trade-off.** Nenhum commit de bootstrap passou por revisão de PR —
aceitável justamente por ser o ponto zero do repositório.

### ADR-5 — Deploy adiado para o PythonAnywhere, não executado agora

**Decisão.** `settings/prod.py` já prepara `ALLOWED_HOSTS` para
`*.pythonanywhere.com` e hardening HTTPS, mas nenhum deploy real
aconteceu nesta fase.
**Alternativas.** Deployar um esqueleto vazio só para validar o pipeline.
**Porquê.** O mantenedor definiu que o deploy é a última etapa, só quando o blog
estiver funcionalmente pronto — decidir a plataforma de deploy cedo
(para já deixar `settings/prod.py` correto) sem executá-lo evita retrabalho
depois sem gerar uma infraestrutura que ficaria ociosa por várias specs.
**Trade-off.** Nenhuma validação real de deploy até lá.

## Impacto no código existente

Nenhum — é o ponto de partida do repositório.

## Estratégia de testes

Sem suíte automatizada (nenhuma lógica de domínio existia ainda). A
verificação foi: `python manage.py check`, o portão de qualidade
(`ruff`/`black`/`mypy`), e uma verificação visual manual via Playwright
(screenshots desktop + mobile da home) antes de considerar o design
system pronto — o mesmo padrão de verificação visual que as specs de
frontend seguintes (002, 003, 004, 005) repetiram.
