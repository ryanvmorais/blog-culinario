---
feature: Descoberta pelos buscadores e pelas redes sociais
status: concluído
date: 2026-11-16
related:
  - 002-listagem-detalhe-receitas/requirements.md
  - 003-busca-e-filtros/requirements.md
  - 008-correcoes-de-interface/requirements.md
  - 009-modo-demonstracao/requirements.md
origin: concepcao
---

# 010 — Descoberta pelos buscadores e pelas redes sociais — Tasks

## Etapa 1 — Endereço público

- [x] `blog_culinario/endereco.py` (novo): `normalizar_url_publica(valor)` (vazio → `""`; esquema `http`/`https`, host, sem usuário, caminho vazio ou `/`, sem query nem fragmento; senão `ImproperlyConfigured` que cita a chave e o formato) e `url_absoluta(caminho)` (`""` sem `URL_PUBLICA`). Só importa `urllib.parse`, `django.conf.settings` e `django.core.exceptions`. — RF-01, RNF-03, ADR-5
- [x] `blog_culinario/settings/base.py`: seção "Descoberta (spec 010)" depois do modo demonstração, com `URL_PUBLICA = normalizar_url_publica(env.str("URL_PUBLICA", default=""))` e comentário do efeito. — RF-01, ADR-5
- [x] `nucleo/test_descoberta.py` (novo): `normalizar_url_publica` parametrizada com os válidos (barra final, porta, `http://`) e os inválidos (sem esquema, `ftp://`, caminho, query, fragmento, usuário e senha); `url_absoluta` com e sem `URL_PUBLICA`. — RF-01, RF-08
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 224 passed (22 novos); ruff/black/mypy verdes

## Etapa 2 — Canonical e Open Graph

- [x] `nucleo/templatetags/__init__.py` e `nucleo/templatetags/metadados.py` (novos): tag `{% capturar nome %}…{% endcapturar %}` com `child_nodelists = ("nodelist",)`, conteúdo sem espaços nas pontas, guardado no contexto como `SafeString`, sem escrever nada no lugar. — RF-03, ADR-2
- [x] `blog_culinario/descoberta.py` (novo): `contexto_descoberta(request)` devolve `url_canonica` (`""` sem `URL_PUBLICA`; senão `url_absoluta(escape_uri_path(request.path))`, mais `?page=N` só em `receitas:lista` com `page` inteiro maior que 1). — RF-02, RNF-03, ADR-3
- [x] `blog_culinario/settings/base.py`: `"blog_culinario.descoberta.contexto_descoberta"` no fim de `context_processors`. — ADR-3
- [x] `templates/base.html`: `{% load static metadados %}`; `titulo` e `descricao` capturados em `titulo_pagina` e `descricao_pagina`, com os textos padrão de hoje; `<title>` e `description` lendo as variáveis; bloco `endereco_canonico` com canonical e `og:url`; bloco `og_tipo` (`website`); `og:title`, `og:description`, `og:site_name` e `og:locale`. Comentários em `{# #}` de uma linha. — RF-02, RF-03, RF-07, ADR-2
- [x] `templates/403.html` e `templates/404.html`: `{% block endereco_canonico %}{% endblock %}`. — RF-02, ADR-3
- [x] `receitas/templates/receitas/detalhe.html`: `{% block og_tipo %}article{% endblock %}`. — RF-03
- [x] `nucleo/test_descoberta.py`: canonical e `og:url` em cada página pública com `HTTP_HOST` diferente do host de `URL_PUBLICA`; query string descartada; lista com `?page=2&q=bolo&categoria=x` → `?page=2`; receita não publicada (404) e 403 sem canonical; sem `URL_PUBLICA`, sem canonical; `og:title` = `<title>`, `og:description` = `description`, `og:site_name`, `og:locale` e `og:type` por tipo, sem `og:image` nem `twitter:card`; `<head>` da home sem `URL_PUBLICA`, tirando as `og:*`, igual ao trecho de hoje. — RF-02, RF-03, RF-07, RF-08, RNF-03
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 241 passed (17 novos); ruff/black/mypy verdes; `<head>` renderizado sem `URL_PUBLICA` comparado com o de antes nas páginas públicas: igual fora das `og:*`

## Etapa 3 — Arquivos de descoberta

- [x] `blog_culinario/descoberta.py`: `SitemapPublico` (`get_protocol` e `get_domain` de `URL_PUBLICA`) e `PaginasSitemap` (`nucleo:home` e `receitas:lista`, `location` por `reverse`). — RF-05, RNF-03, ADR-1
- [x] `receitas/sitemaps.py` (novo): `ReceitaSitemap(SitemapPublico)` com `items()` só de `publicado=True`, `location` por `reverse("receitas:detalhe", …)` e `lastmod` = `atualizado_em`. — RF-05, ADR-1
- [x] `blog_culinario/descoberta.py`: views `robots_txt`, `sitemap` (`Http404` sem `URL_PUBLICA`, senão delega para `django.contrib.sitemaps.views.sitemap`) e `security_txt` (`Http404` sem o modo; `Contact`, `Expires`, `Preferred-Languages`, `Policy` e, com `URL_PUBLICA`, `Canonical`), todas com `require_safe` (desvio 1 do `design.md`), e a constante `EXPIRACAO_SECURITY_TXT = "2027-11-01T00:00:00Z"`. — RF-04, RF-05, RF-06, ADR-4, ADR-6
- [x] `blog_culinario/settings/base.py`: `"django.contrib.sitemaps"` no `INSTALLED_APPS`. — RF-05, RNF-01, ADR-1
- [x] `blog_culinario/urls.py`: rotas `robots.txt` (`robots_txt`), `sitemap.xml` (`sitemap`, com `{"sitemaps": {"paginas": PaginasSitemap, "receitas": ReceitaSitemap}}`) e `.well-known/security.txt` (`security_txt`); docstring do módulo atualizada. — RF-04, RF-05, RF-06
- [x] `nucleo/test_descoberta.py`: `robots.txt` com e sem `URL_PUBLICA` (status, `Content-Type`, linhas); `sitemap.xml` lido com `xml.etree.ElementTree`, com home, lista e só as receitas publicadas, `<loc>` igual ao canonical de cada página, `<lastmod>` igual ao `atualizado_em`, sem `?page`, login nem cadastro, e 404 sem `URL_PUBLICA`; `security.txt` 404 sem o modo, campos obrigatórios, `Contact:` em `https://`, um único `Expires`, `Canonical:` só com `URL_PUBLICA`; `EXPIRACAO_SECURITY_TXT` entre 30 e 366 dias de `timezone.now()`; POST nas três rotas → 405 e HEAD → 200. — RF-04, RF-05, RF-06, RF-08, RNF-03, ADR-6
- [x] Conferência à mão: `DEBUG=False uv run python manage.py check --deploy` sem aviso novo; com `URL_PUBLICA` e `MODO_DEMONSTRACAO=True` no `.env`, abrir os três arquivos e o `<head>` de uma receita no `runserver`. — RNF-02; mesmos avisos da `main` (`mail.E001`, `security.W009` da chave de teste e `security.W021`), nenhum novo; os três arquivos e o `<head>` da lista conferidos no `runserver`, `HEAD /robots.txt` → 200
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`. — 256 passed (15 novos); ruff/black/mypy verdes

## Etapa 4 — CI e documentação

- [x] `.github/workflows/lighthouse.yml`: `URL_PUBLICA: "http://127.0.0.1:8000"` no passo que sobe o servidor, com comentário do motivo (canonical no mesmo host auditado). — RNF-04
- [x] `.env.example`: `URL_PUBLICA=` com formato, efeito e o que fica de fora vazia; comentário do `MODO_DEMONSTRACAO` cita o `security.txt`. — RNF-05
- [x] `README.md` e `README.en.md`, em "Como rodar o projeto localmente": a frase do modo demonstração cita o `security.txt`, e uma frase nova apresenta `URL_PUBLICA`, na mesma posição nos dois; `uv run pytest nucleo/test_readme_en.py` verde. — RNF-05; paridade e impessoalidade verdes
- [x] `CLAUDE.md`: `blog_culinario/endereco.py` e `blog_culinario/descoberta.py` na arquitetura, e `nucleo/templatetags/` na linha do `nucleo`. — RNF-05
- [x] `docs/stack.md`: `django.contrib.sitemaps` na seção do Django. — RNF-05
- [x] `specs/README.md`: linha da 010 no roadmap; `status` concluído nos três arquivos da spec; `## Desvios` e `## Notas de implementação` no `design.md`, se houver o que pôr. — RF-08
- [x] Portão de qualidade: `uv run ruff check .` → `uv run black --check .` → `uv run mypy .` → `uv run pytest`; Lighthouse CI verde no PR. — 256 passed; ruff/black/mypy e `manage.py check` verdes; rastreabilidade conferida; Lighthouse CI roda no PR
