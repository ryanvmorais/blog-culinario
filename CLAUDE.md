# CLAUDE.md

Este arquivo orienta o Claude Code ao trabalhar neste repositório.

## Visão geral do projeto

Blog culinário multipáginas em Django, com propósito educacional: servir de
referência para quem está aprendendo a construir uma aplicação web completa
em Python (modelagem, views, templates, autenticação, admin, segurança).
Stack mínima de propósito — SQLite, CSS puro sem framework, sem build step —
para manter o foco em Django. Deploy na Railway, atrás da Cloudflare: receita
de build em `railpack.json` e configurações em `blog_culinario/settings/prod.py`
(spec 011).

> **Python 3.12 é o piso (`requires-python = ">=3.12"`):** é o mínimo do Django 6.1. O `.python-version` fixa o 3.12 no desenvolvimento, o CI testa do 3.12 ao 3.15 (matriz) e `ruff`, `black` e `mypy` apontam para o 3.12: não use sintaxe exclusiva de versão mais nova (ex.: `except A, B:` sem parênteses, do 3.14).

## Comandos comuns

```bash
# Instalar dependências e criar o ambiente virtual
uv sync

# Rodar o servidor de desenvolvimento
uv run python manage.py runserver

# Criar/aplicar migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Criar um usuário para acessar /admin/
uv run python manage.py createsuperuser

# Dados de demonstração (receitas, capas e comentários; só com DEBUG=True)
uv run python manage.py semear_dados_demo

# Conta pública do modo demonstração (MODO_DEMONSTRACAO=True; idempotente)
uv run python manage.py criar_conta_demonstracao

# Portão de qualidade (nesta ordem)
uv run ruff check .
uv run black --check .
uv run mypy .
uv run pytest

# Rodar um único teste
uv run pytest caminho/para/tests.py::NomeDoTeste::test_caso
```

## Variáveis de ambiente

Só a `SECRET_KEY` é obrigatória em todo ambiente, desenvolvimento inclusive
(sem default no `base.py`; o CI e o Lighthouse usam um placeholder). O resto
tem default seguro no `settings/dev.py`. Ver `.env.example` para a lista
completa e `blog_culinario/settings/prod.py` para o que produção exige a mais
(`ALLOWED_HOSTS` sem default). O caminho do Admin vem do `ADMIN_URL` (padrão
`admin/`): link ou teste que aponte para o Admin usa `reverse("admin:...")`, e o
`robots.txt` nunca cita o caminho.

## Arquitetura

```
blog_culinario/settings/   # base.py (comum) + dev.py / prod.py (por ambiente)
blog_culinario/limitacao.py # rate limit por rede (IP; IPv6 por /64) via cache do Django: login, Admin, cadastro e comentário (spec 006 e adendo)
blog_culinario/site_admin.py # site do Admin com o login limitado, ligado pelo ConfigAdmin no INSTALLED_APPS (spec 006, adendo)
blog_culinario/cache.py    # CacheArquivoAtomico: cache em arquivo com add() e incr() atômicos entre workers (spec 011)
blog_culinario/origem.py   # trava de origem (X-Origin-Verify + ORIGEM_SEGREDO) e ip_do_visitante() (spec 011)
blog_culinario/cabecalhos.py # middleware do Permissions-Policy; a CSP é o SECURE_CSP nativo do base.py (spec 011)
blog_culinario/demonstracao.py # modo demonstração: conta pública, mensagens e context processor (spec 009)
blog_culinario/endereco.py # URL_PUBLICA: validação na subida e url_absoluta() (spec 010)
blog_culinario/descoberta.py # canonical (context processor), sitemaps, robots.txt, sitemap.xml e security.txt (spec 010)
nucleo/                    # a home, a view servir_midia (capas), a tag {% capturar %} (templatetags/metadados.py) e os testes transversais (interface, tema escuro, descoberta, cabeçalhos, hospedagem, limitação de taxa, comentários de template, README em inglês, impessoalidade)
receitas/                  # domínio principal: Receita, Categoria, Tag, Comentario; management/commands/semear_dados_demo.py (dados do Lighthouse CI) e seu teste
usuarios/                  # autenticação (django.contrib.auth); management/commands/criar_conta_demonstracao.py
templates/                 # base.html + includes/ (navbar, rodapé) + 404, 403 e 500
static/css/                # design system: tokens.css (variáveis e tema escuro), fontes.css (@font-face) e base.css
static/fonts/              # Inter e Fraunces (woff2 variável, subconjunto latin, licença OFL)
static/js/, static/img/    # interacoes.js (JS puro, sem build) e favicon.svg
assets/                    # imagens do README e do social preview
specs/                     # spec-driven development — ver specs/README.md
docs/stack.md              # o que compõe a stack, por que e o que estudar
docs/design-system.html    # catálogo visual (tokens, tipografia, componentes); abra direto no navegador — usa o tokens.css e o base.css do site
.github/                   # CI (ci.yml), pip-audit semanal (pip-audit.yml), CodeQL (codeql.yml), Lighthouse CI (lighthouse.yml + lighthouse/), Dependabot (uv + github-actions), formulário de issue (com o atalho para o aviso privado de segurança) e template de PR
SECURITY.md                # política de segurança: relato privado pelos avisos do GitHub, prazos e escopo
railpack.json              # build e start na Railway: uv sync --locked, collectstatic, migrate e gunicorn, sempre com settings.prod (spec 011)
conftest.py                # pytest: cache em pasta temporária, fora da django_cache/ da raiz
```

Cada app novo do domínio segue o padrão de `nucleo`: `views.py` com funções
simples primeiro, `urls.py` com `app_name` namespaced, templates em
`<app>/templates/<app>/`.

## Convenções

- **Idioma do código:** português (classes, funções, variáveis, commits,
  branches, docstrings, comentários, specs e docs). Exceções: strings visíveis
  ao usuário (pt-BR); keywords da linguagem; termos técnicos universais (API,
  HTTP, URL, JSON, SQL, HTML, CSS); nomes impostos por framework (`save`,
  `clean`, `get_queryset`, dunder methods, prefixo `test_`); empréstimos
  naturalizados (`link`, `card`, `layout`, `cache`, `token`, `deploy`); e as
  seções PEP 257 das docstrings (`Args:`, `Returns:`, `Raises:`, `Attributes:`).
- **Estilo de arquivo:** docstring de módulo em todo `.py` e em toda classe ou
  função pública, com o tipo repetido em cada entrada de `Args:`/`Returns:`;
  type hints completos (`mypy` strict); comentários explicam o *porquê*, não o
  *quê*. Siga o estilo do arquivo vizinho.
- **Comentários nos templates:** comentário do Django, `{# #}` numa linha e
  `{% comment %}…{% endcomment %}` em várias (régua de seção e `{# fim: NOME #}`
  inclusive). `<!-- -->` vai para o HTML de cada visitante e o Django executa as
  tags dentro dele; `{# #}` quebrado em linhas aparece como texto. O
  `nucleo/test_comentarios_templates.py` guarda a regra. Exceção: o
  `docs/design-system.html`, que não passa pelo Django.

- **Modo demonstração:** com `MODO_DEMONSTRACAO=True`, cadastro e comentário
  validam mas não gravam. View nova que grave dado de visitante consulta
  `modo_demonstracao_ligado()` antes do `save()` (spec 009, ADR-1).

- **Endereço absoluto só por `url_absoluta()`** (`blog_culinario/endereco.py`),
  que lê `URL_PUBLICA`; nunca do `Host` do pedido (spec 010, RNF-03). Página nova
  que estende o `base.html` ganha canonical e Open Graph sozinha; página de erro
  esvazia o bloco `endereco_canonico`. O `Expires` do `security.txt` é fixo: o
  `nucleo/test_descoberta.py` falha 30 dias antes, e aí se move a data.

- **Hospedagem (spec 011):** banco, mídia e cache saem de `DIRETORIO_DADOS`
  (o volume em produção). View nova que limita por IP usa `limite_excedido()`,
  nunca o `REMOTE_ADDR` direto: o IP real só vem do `CF-Connecting-IP` com a
  trava de origem ligada (`ORIGEM_SEGREDO`). O `mail.E001` fica silenciado no
  `prod.py` porque o blog não envia e-mail; funcionalidade que enviar tira a
  linha e configura o SMTP.

- **CSP (spec 011, ADR-11):** nada inline nos templates (`<script>` sem `src`,
  `<style>`, `style=`, `onclick=`): o `SECURE_CSP` do `base.py` bloquearia, e o
  `nucleo/test_cabecalhos.py` confere o HTML. Script vai para `static/js/`;
  recurso de fora do site pede a origem na diretiva certa do `SECURE_CSP`.

- **README bilíngue:** `README.md` (português) e `README.en.md` (inglês) têm as
  mesmas seções, na mesma ordem. Mudou um, muda o outro no mesmo PR; o
  `nucleo/test_readme_en.py` compara títulos, tabela e links.

## Interface (spec 008)

Regras que a auditoria de interface de 18/10/2026 deixou, guardadas por
`nucleo/test_interface.py` e `nucleo/test_tema_escuro.py`:

- **Botão:** `.botao` herda a fonte (`font: inherit`: o `<button>` do navegador
  não herda e saía em Arial 13 px), tem o rótulo no centro da caixa e 48 px de
  altura. Em formulário, largura dos campos no celular e tamanho do rótulo acima
  de 720 px. Um botão novo segue essas medidas; o `nucleo/test_interface.py`
  guarda as regras de CSS.
- **Alinhamento:** o que é curto e isolado (aviso, formulário de acesso, botão de
  largura total) fica no centro; leitura (receita, comentários, rótulo de campo)
  à esquerda. Aviso que acompanha um título à esquerda segue o título.
- **Cor só por token:** nenhum valor de cor fora do `tokens.css`. O tema escuro é
  um bloco `prefers-color-scheme: dark` com variáveis; mudou uma cor, mude as duas
  paletas (o `test_tema_escuro.py` confere o contraste de cada par).
- **Borda de campo:** `--cor-borda-campo` (3:1); `--cor-borda` é só divisória.
- **Fontes:** hospedadas em `static/fonts/`; não volte ao Google Fonts (LGPD).
- **Cartão:** um link por cartão para teclado e leitor (a foto é `aria-hidden`);
  a lista leva um `h2` oculto entre o `h1` e os `h3`.
- **Mensagens:** na página da receita ficam dentro de `#comentarios`.
- **Erros:** o 500 é HTML completo, sem herdar o `base.html`.

## Qualidade e automação

Sequência do portão: `ruff check` → `black --check` → `mypy` → `pytest`.
CI (`.github/workflows/ci.yml`) roda a mesma sequência em todo PR e em todo
push na `main`. O `.github/workflows/pip-audit.yml` audita o `uv.lock` com
`pip-audit` toda segunda, 09:00 de São Paulo (e à mão): o CI só roda em PR, e o Dependabot nem sempre
abre PR de correção. O `.github/workflows/codeql.yml` roda o CodeQL (Python, JavaScript e os
próprios workflows) em PR, na `main` e aos domingos; os alertas ficam na aba Security. É workflow
do repositório, não o "default setup" do GitHub, que fica desligado: o GitHub não aceita os dois
ao mesmo tempo.

**Lighthouse CI** (`.github/workflows/lighthouse.yml`): audita 5 páginas públicas (home, lista e detalhe de receita, entrar e cadastro), em mobile e desktop, com 3 medições e mediana. Roda em PR quando muda template, estático, view, model, o comando de dados ou a configuração, no push da `main` e à mão (`workflow_dispatch`); repo público, então sem teto de minutos. **Não é check obrigatório** (o Lighthouse varia em runner compartilhado). O servidor sobe com os dados de `manage.py semear_dados_demo` (idempotente, recusa `DEBUG=False`, capas geradas com o Pillow, sem rede) e com `MODO_DEMONSTRACAO=True`, como a instância pública, e `URL_PUBLICA` no host do próprio runner (a auditoria de canonical reprova outro domínio). Limites em `.github/lighthouse/{mobile,desktop}.json`: **erro** para acessibilidade, boas práticas e SEO < 95, CLS > 0,1, peso por página, e `color-contrast`, `unsized-images`, `target-size` e `errors-in-console` como asserções próprias; **aviso** para a nota de Performance. `@lhci/cli` fixado em `LHCI_VERSION` (o Dependabot não vê um `npx`: ao subir, recalibre os limites). Os números são comparação relativa; os reais só existem em produção. Página nova importante entra nos dois JSON; o `receitas/test_semear_dados_demo.py` guarda que toda URL responde 200 e que mobile e desktop auditam o mesmo.

## Spec-driven development

Toda funcionalidade nova (modelagem, views, autenticação, etc.) nasce como uma
spec em `specs/NNN-nome/` antes do código — requisitos → design → tasks, cada
fase com a aprovação do mantenedor. Ver `specs/README.md` para o formato e o
roadmap atual.

## Gestão de dependências

`uv` gerencia o ambiente. Commite `pyproject.toml` **e** `uv.lock`. PRs do
Dependabot (`.github/dependabot.yml`) são revisados um a um (changelog da
versão nova, CI verde), não mergeados automaticamente.

O `[tool.uv]` tem `exclude-newer = "7 days"`: nenhuma resolução pega versão
publicada há menos de 7 dias (a janela do `cooldown` do Dependabot). Correção de
CVE mais nova que isso entra por exceção no `exclude-newer-package`, com
comentário e data para sair; nunca tire a carência inteira.
