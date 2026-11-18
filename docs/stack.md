# Stack do Blog Culinário

Mapa de cada tecnologia que sustenta o projeto: o que faz, por que foi
escolhida contra a alternativa mais óbvia, e o que estudar primeiro para
mexer nela com confiança. Não é exaustivo — o grafo completo de dependências
está no `uv.lock`; decisões de arquitetura mais profundas entram como
`### ADR-N` nas specs de `specs/` conforme o projeto avança.

Como as camadas se encaixam:

```
Navegador
   |  HTML + CSS + JS vanilla (static/, templates/)
   v
Django (views, urls, templates, admin, auth)
   |
   v
SQLite (db.sqlite3)
```

## Linguagem e ambiente

### Python

**O que é/faz:** a linguagem do projeto inteiro — do `manage.py` aos testes.

**Por que esta:** é a linguagem que o projeto se propõe a ensinar (blog
educacional de Python/Django); não havia alternativa em avaliação.

**Qual versão:** o piso é o 3.12, o mínimo que o Django 6.1 aceita; o
`.python-version` fixa o 3.12, e é ele que a Railway usa no deploy. O CI
roda o projeto em todas as versões que o Django 6.1 aceita, do 3.12 ao 3.15, e o `ruff`, o
`black` e o `mypy` apontam para o 3.12, para o próprio lint barrar sintaxe que o
piso não tem.

**O que estudar:** type hints modernos (`X | None`, `list[str]`), f-strings,
compreensões de lista/dict, o módulo `pathlib`.

**Docs:** [Documentação oficial](https://docs.python.org/3/)

### uv

**O que é/faz:** instala as dependências, cria e gerencia o ambiente virtual
(`.venv/`), e resolve/fixa as versões no `uv.lock`.

**Por que esta:** substitui `pip` + `venv` + `pip-tools` por uma ferramenta só,
muito mais rápida (escrita em Rust) e com lockfile determinístico — é o
gerenciador de dependências deste projeto. O `exclude-newer = "7 days"` do
`[tool.uv]` faz o `uv lock` ignorar versões com menos de 7 dias no PyPI (a mesma
carência do Dependabot), a defesa contra pacote sequestrado: uma versão publicada
na última semana ainda não entra no lock.

**O que estudar:** `uv sync`, `uv add`/`uv add --dev`, `uv run`, a diferença entre
`pyproject.toml` (piso mínimo de versão) e `uv.lock` (versão exata resolvida), e o
`exclude-newer` (com o `exclude-newer-package` para a exceção pontual).

**Docs:** [Documentação oficial](https://docs.astral.sh/uv/)

## Framework e dados

### Django

**O que é/faz:** o framework web — roteamento (`urls.py`), ORM (`models.py`),
templates, formulários, admin e autenticação prontos.

**Por que este:** é o objeto de estudo do projeto. Entre os frameworks Python,
Django foi escolhido por vir "com pilhas incluídas" (admin, auth, ORM,
migrations) — dá para ensinar uma aplicação completa sem escolher e integrar
uma dezena de libs separadas, como seria necessário com Flask/FastAPI.

**O que estudar:** o ciclo requisição -> `urls.py` -> view -> template ->
resposta; `QuerySet` e migrations; herança de template (`{% extends %}` +
`{% block %}`); o `django.contrib.admin`; o `django.contrib.sitemaps` e os
context processors, que o projeto usa para o canonical e o `sitemap.xml`
(spec 010); tag de template própria (`{% capturar %}`, em
`nucleo/templatetags/metadados.py`); a Content-Security-Policy nativa do
Django 6 (`SECURE_CSP` e o nonce do `{% csp_nonce_attr %}`, spec 011, ADR-11).

**Docs:** [Documentação oficial](https://docs.djangoproject.com/)

### SQLite

**O que é/faz:** o banco de dados — um único arquivo (`db.sqlite3`), sem processo
de servidor separado.

**Por que este:** zero configuração para quem clona o repositório para estudar —
não exige instalar/subir um Postgres só para rodar `manage.py runserver`. Em
produção, o arquivo fica num volume da plataforma (`DIRETORIO_DADOS`), sem
banco gerenciado para pagar. Trocar por PostgreSQL é só mudar `DATABASES` em
`settings/` — o Django isola o código da engine de banco.

**O que estudar:** migrations (`makemigrations`/`migrate`), o shell do Django
(`manage.py shell`) para explorar o ORM interativamente.

**Docs:** [Documentação oficial](https://docs.djangoproject.com/en/stable/ref/databases/#sqlite-notes)

### Pillow

**O que é/faz:** processa as imagens de capa das receitas (`ImageField` do
Django depende dela para validar/manipular imagem).

**Por que esta:** é a lib padrão de fato do ecossistema Django para `ImageField`
— o próprio framework recomenda.

**O que estudar:** `ImageField` vs `FileField`, os parâmetros `upload_to`,
validação de tipo/tamanho de upload.

**Docs:** [Documentação oficial](https://pillow.readthedocs.io/)

### django-environ

**O que é/faz:** lê `SECRET_KEY`, `ALLOWED_HOSTS`, `ADMIN_URL`, `URL_PUBLICA` e
outras configurações de variáveis de ambiente (arquivo `.env`) em vez de deixá-las hardcoded no `settings.py`.

**Por que esta:** é a forma mais didática de mostrar "segredo fora do código" sem
reinventar um parser de `.env` na mão; alternativa seria `python-decouple`
(equivalente) ou `os.environ` cru (sem valores default/tipados).

**O que estudar:** `environ.Env()`, `env.bool()`/`env.list()`, a precedência
"ambiente real > `.env` > default do código".

**Docs:** [Documentação oficial](https://django-environ.readthedocs.io/)

## Produção

### WhiteNoise

**O que é/faz:** serve os arquivos estáticos (CSS/JS) direto do processo Django
em produção, com compressão e cache-busting por hash.

**Por que esta:** na Railway não há servidor web na frente do gunicorn, e
servir estático direto do Django sem WhiteNoise é lento e sem cache correto. É
a alternativa mais simples a montar Nginx/CDN só para isso. A mídia enviada
pelo Admin (as capas) não passa por ele: o WhiteNoise só indexa arquivos
quando o processo sobe, então as capas saem por uma view fina sobre o
`django.views.static.serve` (`nucleo/views.py`, spec 011).

**O que estudar:** `STORAGES["staticfiles"]`, `collectstatic`, por que
`WhiteNoiseMiddleware` fica logo depois de `SecurityMiddleware`.

**Docs:** [Documentação oficial](https://whitenoise.readthedocs.io/)

### Gunicorn

**O que é/faz:** o servidor WSGI que atende os pedidos em produção, com um ou
mais processos (workers) rodando o `blog_culinario/wsgi.py`.

**Por que esta:** o `runserver` é só para desenvolvimento. O gunicorn é o
servidor WSGI mais usado com Django, sem configuração além do comando de
start. Fica no extra `prod` do `pyproject.toml`: só o build de produção o
instala, e ele não roda no Windows (quem desenvolve lá segue no `runserver`).

**O que estudar:** workers e `WEB_CONCURRENCY`; por que, com mais de um worker,
o cache em memória deixa de servir para a limitação de taxa (cada processo
teria o próprio contador) e o projeto usa um cache em arquivo com `add()` e
`incr()` atômicos (`blog_culinario/cache.py`).

**Docs:** [Documentação oficial](https://docs.gunicorn.org/)

### Railway e Railpack

**O que é/faz:** a plataforma onde roda a demonstração pública. A cada push na
`main`, o Railpack (o construtor da Railway) segue o `railpack.json`: instala
as dependências pelo `uv.lock`, roda o `collectstatic` e, no start, o
`migrate` antes do gunicorn. O banco, as capas e o cache ficam num volume, e o
domínio passa pelo proxy da Cloudflare.

**Por que esta:** deploy a cada push, cobrança por uso e domínio próprio sem
trocar de plano. O `railpack.json` deixa a receita no repositório, onde quem
clona a vê; em outra plataforma, os comandos são os mesmos, no formato dela.

**O que estudar:** `SECURE_PROXY_SSL_HEADER` (HTTPS atrás de proxy), por que o
`migrate` roda no start e não no build (o volume não existe no build), e a
trava de origem (`blog_culinario/origem.py`): como a Cloudflare prova que o
pedido passou por ela antes de o site confiar no `CF-Connecting-IP`.

**Docs:** [Railway](https://docs.railway.com/) · [Railpack](https://railpack.com/)

## Qualidade e testes

### pytest + pytest-django

**O que é/faz:** roda os testes automatizados; o plugin `pytest-django` ensina o
pytest a inicializar o Django (settings, banco de teste) antes de rodar.

**Por que estes:** `pytest` tem sintaxe mais enxuta que o `unittest` embutido do
Django (`assert` simples em vez de `self.assertEqual`) e é o padrão de fato
do ecossistema Python.

**O que estudar:** fixtures do pytest, o marcador `@pytest.mark.django_db`,
`pytest caminho::Teste::test_caso` para rodar um teste só.

**Docs:** [Documentação oficial](https://pytest-django.readthedocs.io/)

### ruff

**O que é/faz:** lint (erros de estilo, imports não usados, bugs comuns) e
organização de imports — substitui flake8 + isort + pyupgrade numa ferramenta
só. Também confere a forma das docstrings (regras `D`, convenção Google, resumo na
segunda linha); docstring ausente ainda não barra o portão.

**Por que esta:** é ordens de magnitude mais rápida que as alternativas
tradicionais e cobre o mesmo conjunto de regras com uma configuração só.

**O que estudar:** `ruff check .`, `ruff check --fix`, a leitura de um código de
regra (`E501`, `F401`) no `pyproject.toml`.

**Docs:** [Documentação oficial](https://docs.astral.sh/ruff/)

### black

**O que é/faz:** formata o código automaticamente — não há debate de estilo, o
formatador decide.

**Por que este:** é o formatador Python de fato mais adotado, não-configurável de
propósito (evita brigas de estilo em equipe/comunidade).

**O que estudar:** `black --check .` (só relata) vs `black .` (aplica).

**Docs:** [Documentação oficial](https://black.readthedocs.io/)

### mypy + django-stubs

**O que é/faz:** checa os type hints estaticamente; `django-stubs` ensina o mypy
a entender os tipos dinâmicos do Django (managers, `QuerySet`, campos de
model).

**Por que estes:** mypy é o type checker de fato do Python; sem `django-stubs`
ele não entende praticamente nada do ORM do Django (managers/campos são
gerados dinamicamente).

**O que estudar:** `mypy .`, o que `[tool.django-stubs] django_settings_module`
faz, como ler um erro `[import-untyped]`/`[arg-type]`.

**Docs:** [Documentação oficial](https://github.com/typeddjango/django-stubs)

## Peças menores

| Peça | Papel |
|---|---|
| Fraunces | Tipografia de título do design system — serifada, editorial. Hospedada em `static/fonts/` (licença OFL), não no Google Fonts: sem requisição a terceiros. |
| Inter | Tipografia de corpo — legibilidade em tela. Também hospedada em `static/fonts/`; as duas são declaradas em `static/css/fontes.css`. |
| `django.contrib.humanize` | Filtros de template (`timesince`, `intcomma`) nas páginas de receita. |
| WhiteNoise (dev) | Também ativo em desenvolvimento — evita duas configurações de estático divergentes. |
| `static/js/interacoes.js` | JS puro, sem framework nem build, carregado com `defer` no `base.html`. Hoje cuida do menu mobile (teclado, `aria-expanded`, Esc, clique fora e Tab no último item de volta ao X). |
| GitHub Actions | `ci.yml` roda o portão de qualidade (ruff, black, mypy, pytest) em todo PR e em todo push na `main`, numa matriz do Python 3.12 (o piso) ao 3.15. |
| Dependabot | `.github/dependabot.yml` abre PRs de atualização para o `uv` e para as próprias Actions; os PRs são revisados, não mergeados sozinhos. |
| pip-audit | `pip-audit.yml` audita o `uv.lock` atrás de CVEs toda segunda, 09:00 de São Paulo (e sob demanda): o CI só roda em PR e o Dependabot nem sempre abre PR de correção. |
| CodeQL | `codeql.yml` roda o code scanning do GitHub (Python, JavaScript e os próprios workflows, sem build) em todo PR, em todo push na `main` e aos domingos; os alertas aparecem na aba Security. Fica no repositório, e não no "default setup", para o runner e as versões serem fixos como nos outros workflows. Estudar primeiro: o `codeql.yml` e a aba Security → Code scanning. |
| Lighthouse CI | `lighthouse.yml` mede as 5 páginas públicas em mobile e desktop e falha se acessibilidade, SEO, contraste, alvo de toque, erro de console, CLS ou peso regredirem. Sobe o site com os dados de `manage.py semear_dados_demo`. Não é check obrigatório (varia em runner compartilhado). Estudar primeiro: `.github/lighthouse/*.json` (os limites) e o `semear_dados_demo.py`. |

## O que deliberadamente não está na stack

- **PostgreSQL/MySQL** — SQLite já resolve o objetivo educacional e cabe num
  volume da plataforma; trocar depois é uma mudança de configuração, não de
  código.
- **React/Vue/Next.js e qualquer build step de frontend** — o projeto ensina
  Django, não uma stack de SPA; HTML + CSS + JS vanilla mantém o foco e
  reduz o que quem está aprendendo precisa instalar.
- **Tailwind CSS** — um design system pequeno em CSS puro (custom properties)
  é mais didático para quem nunca montou uma identidade visual do zero; um
  framework utilitário esconderia essa aprendizagem.
- **django-csp** — o Django 6 já envia a Content-Security-Policy pelo
  `SECURE_CSP`, e o Admin marca as próprias tags com o nonce dela; o pacote
  seria uma dependência a mais para o mesmo cabeçalho.
- **django-allauth** (ou outra lib de autenticação) — o `django.contrib.auth`
  nativo é suficiente para o escopo do projeto e mais transparente para
  quem está aprendendo como autenticação funciona por baixo dos panos.
- **Docker/Docker Compose** — sem serviço externo (banco é SQLite em
  arquivo), não há múltiplos containers para orquestrar; o Railpack monta a
  imagem a partir do `railpack.json`, sem Dockerfile para manter.
- **Redis/Celery** — nenhuma tarefa assíncrona é necessária, e o cache da
  limitação de taxa entre os workers fica em arquivo, no volume, sem um
  serviço a mais para pagar.
