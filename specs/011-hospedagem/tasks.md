---
feature: Hospedagem da demonstração na Railway
status: em andamento
date: 2026-11-16
related:
  - 006-limitacao-de-taxa/requirements.md
  - 009-modo-demonstracao/requirements.md
  - 010-descoberta/requirements.md
origin: concepcao
---

# 011 — Hospedagem da demonstração na Railway — Tasks

## Etapa 1 — Receita de build e configurações de produção no start

- [x] `pyproject.toml`: `[project.optional-dependencies]` com `prod = ["gunicorn>=26.2.0"]`, e `uv lock` respeitando o cooldown de 7 dias (`--exclude-newer` com a data de 7 dias atrás: as versões 27.0.0 e 27.0.1 ficam de fora até lá). — RF-01, RNF-01
- [x] `railpack.json` (novo): o do `design.md`, com `uv sync --locked --no-dev --extra prod`, o `collectstatic` com `DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod` e o start com `export DJANGO_SETTINGS_MODULE=…`, `migrate --noinput` e `gunicorn blog_culinario.wsgi:application --bind 0.0.0.0:${PORT:-8000}`. — RF-01, RF-02, ADR-1, ADR-2, ADR-3
- [x] `blog_culinario/wsgi.py` e `blog_culinario/asgi.py`: padrão `blog_culinario.settings.prod` no `setdefault`; docstrings sem o PythonAnywhere, dizendo que o `manage.py` segue com as de desenvolvimento. — RF-02, ADR-2
- [x] `nucleo/test_hospedagem.py` (novo): a receita lida como JSON (`--locked`, `--no-dev`, `--extra prod`, `collectstatic` com `settings.prod`, `migrate` antes de `gunicorn`, `settings.prod` no start, `${PORT:-8000}`); helper que roda `python -c` num `subprocess` com o ambiente pedido e devolve JSON; o `wsgi.py` importado sem `DJANGO_SETTINGS_MODULE` carregando `settings.prod`. — RF-01, RF-02, RF-13
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 261 passed (5 novos); ruff/black/mypy verdes

## Etapa 2 — Atrás do proxy e operação

- [x] `blog_culinario/settings/base.py`: `DIRETORIO_DADOS` (seção própria, com comentário) e `DATABASES`/`MEDIA_ROOT` a partir dele. — RF-06
- [x] `blog_culinario/settings/prod.py`: `ALLOWED_HOSTS` sem espaços nem itens vazios, `SECURE_PROXY_SSL_HEADER`, `LOGGING` (raiz em WARNING no `StreamHandler`, `django.request` em ERROR) e `SILENCED_SYSTEM_CHECKS = ["mail.E001"]`, cada um com o comentário do `design.md`; docstring e comentários sem o PythonAnywhere. — RF-03, RF-05, RF-11, RF-12, ADR-7, ADR-8
- [x] `.gitignore`: `django_cache/` na seção de dados gerados. — RF-06
- [x] `nucleo/test_hospedagem.py`: pelo helper de `subprocess`, `ALLOWED_HOSTS` com espaços, vírgula no fim, vazia e ausente (subida falha); `DIRETORIO_DADOS` ausente, absoluto e relativo (banco, mídia, cache); `SECURE_PROXY_SSL_HEADER`, `LOGGING` e `SILENCED_SYSTEM_CHECKS` em produção e ausentes em desenvolvimento; `manage.py check --deploy` com saída 0 e só o `security.W021`; o `LOGGING` aplicado com `dictConfig`, ERROR no `stderr` e WARNING do `django.request` fora dele. — RF-05, RF-06, RF-11, RF-12, RF-13
- [x] `nucleo/test_hospedagem.py`: proxy e CSRF com `override_settings` (redirect, cookies seguros, `SECURE_PROXY_SSL_HEADER`, domínio de exemplo em `ALLOWED_HOSTS` e no `HTTP_HOST`): GET com `X-Forwarded-Proto: https` → 200 e `csrftoken` `secure`, sem ele → 301; POST do login com `enforce_csrf_checks=True`, `Origin` do mesmo domínio passa, de outro site → 403. — RF-03, RF-04, RF-13
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 277 passed (16 novos); ruff/black/mypy verdes; check --deploy só com o security.W021 (1 silenciado)

## Etapa 3 — Cache em arquivo e contagem atômica

- [x] `blog_culinario/cache.py` (novo): `CacheArquivoAtomico(FileBasedCache)` com a trava `reserva.lock` (`django.core.files.locks`, `LOCK_EX`); `add()` herdado dentro da trava; `incr()` dentro da trava, lendo validade e valor do arquivo da chave, `ValueError` se ausente ou expirada, e regravando com o tempo que faltava. — RF-08, ADR-4
- [x] `blog_culinario/settings/base.py`: `CACHES` com `CacheArquivoAtomico` em `DIRETORIO_DADOS / "django_cache"`. — RF-06, RF-08, ADR-4
- [x] `conftest.py` (novo, na raiz): fixture `autouse` que põe o `LOCATION` do cache no `tmp_path` pela fixture `settings`. — RNF-04
- [x] `blog_culinario/limitacao.py`: contagem por `cache.add(chave, 0, timeout=janela)` + `cache.incr(chave)`, nova tentativa de `add()` + `incr()` no `ValueError`, e `tentativas > limite`; docstrings do módulo e da função atualizadas (backend em arquivo, contagem atômica). — RF-08
- [x] `nucleo/test_hospedagem.py`: duas instâncias na mesma pasta veem a mesma contagem; um `subprocess` soma na mesma pasta e a soma aparece; threads com `limite_excedido()` simultâneo aceitam no máximo `limite`; `incr()` preserva a validade e levanta `ValueError` em chave ausente ou expirada; `clear()` não apaga o `reserva.lock`. — RF-08, RF-13
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest` (os testes das specs 006 e 007 seguem passando com o cache novo). — 283 passed (6 novos); ruff/black/mypy verdes; os testes das specs 006 e 007 passam com o cache novo; nenhuma django_cache/ criada na raiz (desvio 1)

## Etapa 4 — Trava de origem e IP do visitante

- [x] `blog_culinario/origem.py` (novo): `CABECALHO_ORIGEM`, `CABECALHO_IP`, `trava_de_origem_ligada()`, `OrigemCloudflareMiddleware` (`hmac.compare_digest`, aviso no log com método e caminho, `PermissionDenied`) e `ip_do_visitante()` (`CF-Connecting-IP` válido só com a trava ligada, senão `REMOTE_ADDR`). — RF-09, RF-10, RF-11, RNF-05, ADR-5
- [x] `blog_culinario/settings/base.py`: `ORIGEM_SEGREDOS` (seção "Trava de origem (spec 011)") e o middleware no topo do `MIDDLEWARE`. — RF-09, ADR-5
- [x] `blog_culinario/limitacao.py`: IP por `ip_do_visitante()`; docstring do `request` atualizada. — RF-10
- [x] `nucleo/test_hospedagem.py`: sem segredo → 200; com segredo, sem cabeçalho e com valor errado → 403 com o `403.html`, com o atual e com o anterior → 200; `caplog` com método e caminho e sem o valor recebido; `ip_do_visitante()` com a trava ligada (cabeçalho válido, ausente, inválido) e desligada (cabeçalho ignorado); `limite_excedido()` com dois `CF-Connecting-IP` diferentes contando separado só com a trava ligada. — RF-09, RF-10, RF-11, RF-13, RNF-05
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 297 passed (14 novos); ruff/black/mypy verdes

## Etapa 5 — Mídia com `DEBUG=False`

- [x] `nucleo/views.py`: `servir_midia(request, caminho)` com `require_safe`, `cache_control(public=True, max_age=86400)`, `serve(..., document_root=settings.MEDIA_ROOT)` e `SuspiciousFileOperation` convertido em `Http404`. — RF-07, ADR-6
- [x] `blog_culinario/urls.py`: rota `f"{settings.MEDIA_URL.lstrip('/')}<path:caminho>"` → `servir_midia` (`name="midia"`) no lugar do `static()` com `DEBUG`; docstring e comentário do módulo atualizados. — RF-07, ADR-6
- [x] `nucleo/test_hospedagem.py`: com `DEBUG=False` e `MEDIA_ROOT` no `tmp_path`, JPEG → 200, `image/jpeg`, `nosniff`, `max-age=86400`; inexistente, pasta e `../` → 404 com o `404.html`; POST → 405; com `DEBUG=True`, a capa segue servida. — RF-07, RF-13
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 305 passed (8 novos); ruff/black/mypy verdes

## Etapa 6 — Documentação e conferência local

- [x] `.env.example`: `DIRETORIO_DADOS`, `ORIGEM_SEGREDO` e `ORIGEM_SEGREDO_ANTERIOR` (como gerar o valor com `secrets.token_urlsafe`, o cabeçalho `X-Origin-Verify` e o efeito no IP), `ALLOWED_HOSTS` com exemplo de domínio próprio e o aviso de que, atrás de proxy sem a trava, todos os visitantes dividem o limite de taxa. — RNF-06
- [x] `README.md` e `README.en.md`: seção de deploy com a receita (`railpack.json`), as variáveis, o volume e a trava de origem, nas mesmas seções e na mesma ordem; o PythonAnywhere fora. — RNF-06
- [x] `CLAUDE.md`: visão geral (destino de deploy), nota do piso do Python só pelo mínimo do Django 6.1, arquitetura (`railpack.json`, `cache.py`, `origem.py`) e a convenção de que view nova que limita por IP usa `limite_excedido()`, nunca o `REMOTE_ADDR` direto. — RNF-06
- [x] `docs/stack.md`: Railway, Railpack e gunicorn; SQLite, WhiteNoise e cache revistos sem o PythonAnywhere. — RNF-06
- [x] Busca por `PythonAnywhere` e `pythonanywhere` fora de `specs/` concluídas: nenhuma ocorrência. — RNF-06
- [x] Conferência à mão: `check --deploy` com as configurações de produção; `runserver` com `settings.prod`, `--insecure`, `ORIGEM_SEGREDO` e `DIRETORIO_DADOS` numa pasta temporária, conferindo com `curl` o 403 sem o cabeçalho, o 200 com ele e com `X-Forwarded-Proto: https`, e uma capa em `/media/`. — RF-03, RF-06, RF-07, RF-09, RF-12
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest` (o `nucleo/test_readme_en.py` confere a paridade dos READMEs). — 307 testes (2 novos da chave secreta): 305 passed e 2 skipped com um .env local (os de variável ausente; sem .env, passam); ruff/black/mypy verdes; conferência à mão com curl: 403 sem o segredo (com 403.html e aviso no log sem o valor), 301 para HTTPS, 200 com os dois cabeçalhos, capa image/jpeg com nosniff, max-age e HSTS, ../ em 404

## Etapa 6b — Variáveis com o nome do Django, Admin configurável e chave obrigatória

- [x] Renomear `DJANGO_SECRET_KEY` → `SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` → `ALLOWED_HOSTS` em código, testes, `.env.example`, docs e specs (a 000 e a 010 só nos nomes). — decisão resolvida 10
- [x] `base.py`: `SECRET_KEY` sem default e `ADMIN_URL` normalizado; `prod.py` sem a linha da chave; `urls.py` com `path(settings.ADMIN_URL, ...)`; `robots.txt` com `Allow: /`. — RF-14, RF-15, ADR-9, ADR-10
- [x] `ci.yml` e `lighthouse.yml`: `SECRET_KEY` placeholder no `env` do job. — RF-15
- [x] Testes: `ADMIN_URL` (leitura e rota), chave ausente ou vazia em dev e prod, `robots.txt` sem o Admin, `meta robots` no login do Admin, testes do Admin por `reverse`. — RF-13, RF-14, RF-15
- [x] `.env.example`, `README.md`, `README.en.md` ("Como rodar": copiar o `.env.example` e gerar a chave) e `CLAUDE.md`. — RNF-06
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 319 testes: 316 passed e 3 skipped com um .env local (os de variável ausente; sem o .env, passam); ruff/black/mypy verdes

## Etapa 6c — Content-Security-Policy e Permissions-Policy

- [x] `base.py`: `SECURE_CSP`, o `ContentSecurityPolicyMiddleware` e o context processor `csp`; `blog_culinario/cabecalhos.py` com o `PermissionsPolicyMiddleware` no fim do `MIDDLEWARE`. — RF-16, RF-17, ADR-11
- [x] Testes em `nucleo/test_cabecalhos.py`: a política nas páginas públicas e no Admin, o HTML público sem nada inline, o nonce no `<style>` do Admin e o `Permissions-Policy`. — RF-13, RF-16, RF-17, RNF-02
- [x] Conferência à mão no Chrome: páginas públicas e dez telas do Admin (lista, inclusão, edição e exclusão de receita, usuários, troca de senha) sem violação de CSP no console. — RF-16
- [x] `CLAUDE.md`: `cabecalhos.py` na arquitetura e a convenção de que nada é inline. — RNF-06
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 324 testes: 321 passed e 3 skipped com um .env local (os de variável ausente); ruff/black/mypy verdes

## Etapa 7 — Com a demonstração publicada

- [ ] Conferência de fora, no endereço público: redirect 301 de HTTP para HTTPS, HSTS, `nosniff`, `X-Frame-Options`, `Content-Security-Policy` e `Permissions-Policy`, cookie CSRF com `Secure`, uma capa em `/media/` e `../` em 404, login com a conta de demonstração, POST com `Origin` de outro site em 403, a sexta senha errada recusada e o `migrate` antes do gunicorn no log do deploy. — RF-01, RF-03, RF-04, RF-07, RF-08, RF-10, RF-16, RF-17
- [ ] `README.md` e `README.en.md`: link da demonstração, com o endereço já respondendo com o conteúdo carregado. — RNF-06
- [ ] `specs/011-hospedagem/` (os três arquivos) e `specs/README.md`: status `concluído`; `design.md` com `## Desvios` e `## Notas de implementação` (suíte antes e depois, `check --deploy`, o que foi conferido no ar). —
- [ ] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. —
