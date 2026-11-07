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

**Qual versão:** o piso é o 3.12, que é a versão do servidor no PythonAnywhere
(a plataforma lista Python só até o 3.13) e o mínimo que o Django 6.1 aceita. O CI
roda o projeto no 3.12 e no 3.14 (o mais novo que o Django 6.1 aceita), e o `ruff`, o
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
gerenciador de dependências deste projeto.

**O que estudar:** `uv sync`, `uv add`/`uv add --dev`, `uv run`, a diferença entre
`pyproject.toml` (piso mínimo de versão) e `uv.lock` (versão exata resolvida).

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
`{% block %}`); o `django.contrib.admin`.

**Docs:** [Documentação oficial](https://docs.djangoproject.com/)

### SQLite

**O que é/faz:** o banco de dados — um único arquivo (`db.sqlite3`), sem processo
de servidor separado.

**Por que este:** zero configuração para quem clona o repositório para estudar —
não exige instalar/subir um Postgres só para rodar `manage.py runserver`. É
também o banco suportado sem custo extra no plano gratuito do PythonAnywhere,
o alvo de deploy do projeto. Trocar por PostgreSQL é só mudar `DATABASES` em
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

**O que é/faz:** lê `SECRET_KEY`, `DEBUG` e outras configurações de variáveis de
ambiente (arquivo `.env`) em vez de deixá-las hardcoded no `settings.py`.

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

**Por que esta:** o PythonAnywhere (destino de deploy) não exige um servidor de
arquivos estáticos dedicado, mas servir estático direto do Django sem
WhiteNoise é lento e sem cache correto. É a alternativa mais simples a montar
Nginx/CDN só para isso.

**O que estudar:** `STORAGES["staticfiles"]`, `collectstatic`, por que
`WhiteNoiseMiddleware` fica logo depois de `SecurityMiddleware`.

**Docs:** [Documentação oficial](https://whitenoise.readthedocs.io/)

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
| `static/js/interacoes.js` | JS puro, sem framework nem build, carregado com `defer` no `base.html`. Hoje cuida do menu mobile (teclado, `aria-expanded`, Esc e clique fora). |
| GitHub Actions | `ci.yml` roda o portão de qualidade (ruff, black, mypy, pytest) em todo PR e em todo push na `main`, numa matriz com Python 3.12 (o piso) e 3.14. |
| Dependabot | `.github/dependabot.yml` abre PRs de atualização para o `uv` e para as próprias Actions; os PRs são revisados, não mergeados sozinhos. |
| pip-audit | `pip-audit.yml` audita o `uv.lock` atrás de CVEs toda segunda, 09:00 de São Paulo (e sob demanda): o CI só roda em PR e o Dependabot nem sempre abre PR de correção. |
| Lighthouse CI | `lighthouse.yml` mede as 5 páginas públicas em mobile e desktop e falha se acessibilidade, SEO, contraste, alvo de toque, erro de console, CLS ou peso regredirem. Sobe o site com os dados de `manage.py semear_dados_demo`. Não é check obrigatório (varia em runner compartilhado). Estudar primeiro: `.github/lighthouse/*.json` (os limites) e o `semear_dados_demo.py`. |

## O que deliberadamente não está na stack

- **PostgreSQL/MySQL** — SQLite já resolve o objetivo educacional e roda de
  graça no PythonAnywhere; trocar depois é uma mudança de configuração, não
  de código.
- **React/Vue/Next.js e qualquer build step de frontend** — o projeto ensina
  Django, não uma stack de SPA; HTML + CSS + JS vanilla mantém o foco e
  reduz o que quem está aprendendo precisa instalar.
- **Tailwind CSS** — um design system pequeno em CSS puro (custom properties)
  é mais didático para quem nunca montou uma identidade visual do zero; um
  framework utilitário esconderia essa aprendizagem.
- **django-allauth** (ou outra lib de autenticação) — o `django.contrib.auth`
  nativo é suficiente para o escopo do projeto e mais transparente para
  quem está aprendendo como autenticação funciona por baixo dos panos.
- **Docker/Docker Compose** — sem serviço externo (banco é SQLite em
  arquivo), não há múltiplos containers para orquestrar; o PythonAnywhere
  também não espera uma imagem Docker.
- **Redis/Celery** — nenhuma tarefa assíncrona ou cache distribuído é
  necessária no escopo atual do blog.
