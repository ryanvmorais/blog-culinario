---
feature: Hospedagem da demonstração na Railway
status: concluído
date: 2026-11-16
related:
  - 006-limitacao-de-taxa/requirements.md
  - 009-modo-demonstracao/requirements.md
  - 010-descoberta/requirements.md
origin: concepcao
---

# 011 — Hospedagem da demonstração na Railway — design

## Visão geral da abordagem

A Railway constrói o projeto com o Railpack, o construtor padrão dela, a partir de um
`railpack.json` na raiz. O arquivo fixa os comandos: no build, `uv sync` pelo lock e
`collectstatic`; no start, `migrate` e o gunicorn na porta `PORT`. Cada comando que
carrega o Django leva `DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod` na própria
linha, e o `wsgi.py` passa a cair nas configurações de produção, não nas de
desenvolvimento (ADR-2).

As configurações seguem em pacote (`base.py`, `dev.py`, `prod.py`). O `base.py` ganha
`DIRETORIO_DADOS`, de onde saem o banco, a mídia e o cache; o cache passa a ser um
backend em arquivo do próprio projeto, com `add()` e `incr()` atômicos entre processos
(ADR-4). O `prod.py` ganha o cabeçalho do proxy, o `LOGGING` para a saída de erro, a
leitura tolerante de `ALLOWED_HOSTS` e o silêncio justificado do `mail.E001`.

Um middleware novo, primeiro da lista, recusa com 403 o pedido sem o segredo de origem
quando `ORIGEM_SEGREDO` está definida. A limitação de taxa passa a pedir o IP a uma
função que só confia no `CF-Connecting-IP` com essa trava ligada, e a contar com
`add()` + `incr()`, que o backend novo torna atômicos. A mídia é servida por uma view
fina sobre o `django.views.static.serve`, com e sem `DEBUG`.

## Layout de módulos

| Arquivo | Muda | O quê |
|---|---|---|
| `railpack.json` | novo | build e start (RF-01, RF-02) |
| `pyproject.toml`, `uv.lock` | muda | extra `prod` com o gunicorn (RF-01, RNF-01) |
| `blog_culinario/wsgi.py`, `blog_culinario/asgi.py` | muda | padrão `settings.prod`; docstring sem o PythonAnywhere (RF-02) |
| `blog_culinario/settings/base.py` | muda | `DIRETORIO_DADOS`, `CACHES`, `ORIGEM_SEGREDOS`, o middleware (RF-06, RF-08, RF-09) |
| `blog_culinario/settings/prod.py` | muda | `ALLOWED_HOSTS`, `SECURE_PROXY_SSL_HEADER`, `LOGGING`, `SILENCED_SYSTEM_CHECKS`; docstring e comentários sem o PythonAnywhere (RF-03, RF-05, RF-11, RF-12) |
| `blog_culinario/cache.py` | novo | `CacheArquivoAtomico` (RF-08, ADR-4) |
| `blog_culinario/origem.py` | novo | `OrigemCloudflareMiddleware`, `trava_de_origem_ligada()` e `ip_do_visitante()` (RF-09, RF-10, ADR-5) |
| `blog_culinario/limitacao.py` | muda | IP por `ip_do_visitante()`, contagem por `add()` + `incr()` (RF-08, RF-10) |
| `nucleo/views.py` | muda | view `servir_midia` (RF-07) |
| `blog_culinario/urls.py` | muda | rota de mídia sempre ligada, no lugar do `static()` só com `DEBUG` (RF-07) |
| `conftest.py` | novo | fixture automática que põe o cache de cada teste numa pasta temporária (RNF-04) |
| `nucleo/test_hospedagem.py` | novo | a suíte do RF-13 |
| `blog_culinario/settings/base.py` (CSP) | muda | `SECURE_CSP`, os dois middlewares e o context processor `csp` (RF-16, RF-17, ADR-11) |
| `blog_culinario/cabecalhos.py` | novo | `PermissionsPolicyMiddleware` e `PERMISSIONS_POLICY` (RF-17) |
| `nucleo/test_cabecalhos.py` | novo | a parte do RF-13 que cobre a CSP e o `Permissions-Policy` |
| `.gitignore` | muda | `django_cache/` |
| `.env.example`, `README.md`, `README.en.md`, `CLAUDE.md`, `docs/stack.md` | muda | variáveis, receita de build, trava de origem, PythonAnywhere fora (RNF-06) |

## Modelo de dados

Nenhuma mudança. Nenhuma migration.

## Componentes

### `railpack.json`

```json
{
  "$schema": "https://schema.railpack.com",
  "steps": {
    "build": {
      "commands": [
        "uv sync --locked --no-dev --extra prod",
        "DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod python manage.py collectstatic --noinput"
      ]
    }
  },
  "deploy": {
    "startCommand": "export DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod && python manage.py migrate --noinput && gunicorn blog_culinario.wsgi:application --bind 0.0.0.0:${PORT:-8000}"
  }
}
```

- `--locked` falha se o lock não bater com o `pyproject.toml` (RF-01); o CI segue com
  `uv sync --all-extras --dev`.
- O Railpack roda cada comando em texto como `sh -c`, então a variável na frente do
  comando e o `&&` valem. O `collectstatic` precisa das configurações de produção: é o
  `CompressedManifestStaticFilesStorage` delas que grava o `staticfiles.json`, sem o
  qual toda página com estático responde 500.
- O `collectstatic` importa as configurações de produção, que exigem
  `SECRET_KEY` e `ALLOWED_HOSTS`: na Railway, as variáveis do serviço
  valem também no build.
- O número de workers não fica no comando: o gunicorn lê `WEB_CONCURRENCY` (padrão 1).

### `blog_culinario/wsgi.py` e `asgi.py`

O `os.environ.setdefault("DJANGO_SETTINGS_MODULE", ...)` passa de `settings.dev` para
`settings.prod`. O `manage.py` segue com `settings.dev`, e o `runserver` não lê esse
padrão: ele importa o `wsgi.py` depois de o `manage.py` já ter definido a variável
(RF-02).

### `blog_culinario/settings/base.py`

```python
# Pasta dos dados graváveis: banco, mídia enviada pelo Admin e cache da
# limitação de taxa. Em produção, o caminho do volume montado pela plataforma.
# Vazia: a raiz do repositório, como antes (Path / "" é o próprio Path).
DIRETORIO_DADOS = BASE_DIR / env.str("DIRETORIO_DADOS", default="").strip()
```

Um caminho absoluto (`/data`) substitui o `BASE_DIR`; um relativo (`dados`) fica dentro
dele. `DATABASES["default"]["NAME"]` passa a `DIRETORIO_DADOS / "db.sqlite3"` e
`MEDIA_ROOT` a `DIRETORIO_DADOS / "media"` (RF-06).

```python
CACHES = {
    "default": {
        "BACKEND": "blog_culinario.cache.CacheArquivoAtomico",
        "LOCATION": DIRETORIO_DADOS / "django_cache",
    }
}
```

```python
# Trava de origem (spec 011): com um segredo definido, só passa o pedido que
# traz o cabeçalho X-Origin-Verify com ele. O anterior vale durante a troca.
ORIGEM_SEGREDOS = tuple(
    segredo
    for segredo in (
        env.str("ORIGEM_SEGREDO", default="").strip(),
        env.str("ORIGEM_SEGREDO_ANTERIOR", default="").strip(),
    )
    if segredo
)
```

O `"blog_culinario.origem.OrigemCloudflareMiddleware"` entra no topo do `MIDDLEWARE`,
antes do `SecurityMiddleware`: o que não veio pelo proxy não chega a nenhuma outra
camada, nem ao redirect de HTTPS (RF-09).

A CSP (RF-16, ADR-11) fica no `base.py`, igual nos dois ambientes:

```python
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF, CSP.NONCE],
    "img-src": [CSP.SELF],
    "font-src": [CSP.SELF],
    "base-uri": [CSP.NONE],
    "form-action": [CSP.SELF],
    "object-src": [CSP.NONE],
    "frame-ancestors": [CSP.NONE],
}
```

O `django.middleware.csp.ContentSecurityPolicyMiddleware` e o
`blog_culinario.cabecalhos.PermissionsPolicyMiddleware` entram no fim do
`MIDDLEWARE`, e o `django.template.context_processors.csp` entra nos
`context_processors`: é ele que entrega o nonce ao `{% csp_nonce_attr %}` dos
templates do Admin. O nonce só é gerado quando um template o usa, então nas páginas
públicas o `CSP.NONCE` some do cabeçalho e a política é a mesma a cada pedido.

### `blog_culinario/cabecalhos.py`

`PermissionsPolicyMiddleware` acrescenta `PERMISSIONS_POLICY` a toda resposta com
`response.setdefault(...)`. Os nomes são só os que o Chrome
reconhece: um desconhecido vira erro no console, e o Lighthouse CI reprova erro de
console (RF-17).

### `blog_culinario/settings/prod.py`

```python
# Lista separada por vírgula; espaços e vírgula sobrando não viram host.
ALLOWED_HOSTS = [
    host.strip() for host in env.list("ALLOWED_HOSTS") if host.strip()
]
```

Sem default: ausente, o `django-environ` levanta `ImproperlyConfigured` e a subida
falha; vazia, a lista fica `[]` e todo host é recusado (RF-05).

```python
# Atrás do proxy da plataforma o TLS termina antes do Django, que recebe HTTP.
# O proxy avisa o protocolo original neste cabeçalho; sem lê-lo, o
# SECURE_SSL_REDIRECT redireciona para sempre. Num servidor que entrega o
# Django direto à internet, sem proxy, tire esta linha.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

```python
# O LOGGING padrão do Django só manda o erro 500 por e-mail aos ADMINS, que o
# projeto não define: sem isto, o erro não aparece no log do serviço.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    # 404 e 403 saem como WARNING no django.request; ERROR deixa só o 500.
    "loggers": {"django.request": {"level": "ERROR"}},
}
```

```python
# O blog não envia e-mail (spec 011, decisão resolvida 8): o backend de console
# do base.py só existe porque o Django exige um. Uma funcionalidade que passe a
# enviar e-mail configura o SMTP aqui e tira esta linha.
SILENCED_SYSTEM_CHECKS = ["mail.E001"]
```

### `blog_culinario/cache.py`

`CacheArquivoAtomico(FileBasedCache)`, no molde do backend de mesmo nome do projeto
irmão `portfolio-dinamico`. Uma trava exclusiva de arquivo (`django.core.files.locks`,
`LOCK_EX`) num arquivo `reserva.lock` da pasta do cache, fora do padrão `*.djcache`
(o `_cull()` e o `clear()` não a apagam). Valem entre threads e entre os processos do
gunicorn.

- `add()`: o `add()` herdado (`has_key()` e depois `set()`) dentro da trava.
- `incr()`: dentro da mesma trava, lê o arquivo da chave (a validade, gravada primeiro,
  e o valor), levanta `ValueError` se ele não existe ou já expirou (o contrato do
  `BaseCache`), e grava o valor somado com o tempo que **faltava** para a validade. O
  `incr()` herdado do `BaseCache` faz `get()` + `set()` sem trava e grava com o
  `TIMEOUT` padrão do `CACHES`, o que reiniciaria a janela da limitação a cada
  tentativa (spec 006, RF-03). O `LocMemCache` já preserva a validade no `incr()`; o
  backend novo passa a se comportar igual.
- `get()`, `set()` e `delete()` ficam como no Django.

### `blog_culinario/origem.py`

```python
CABECALHO_ORIGEM = "HTTP_X_ORIGIN_VERIFY"
CABECALHO_IP = "HTTP_CF_CONNECTING_IP"
```

- `trava_de_origem_ligada() -> bool`: `bool(settings.ORIGEM_SEGREDOS)`, lido a cada
  chamada (a troca de segredo e o `override_settings` dos testes valem na hora).
- `OrigemCloudflareMiddleware`: com a trava desligada, repassa o pedido. Ligada,
  compara o cabeçalho recebido com cada segredo por `hmac.compare_digest` (tempo
  constante, RNF-05). Sem igualdade, registra `logger.warning("pedido sem o segredo
  de origem: %s %s", request.method, request.path)`, sem o valor recebido (RF-11,
  RNF-05), e levanta `PermissionDenied`. O Django converte a exceção do middleware
  na resposta do `handler403`, que renderiza o `templates/403.html` (RF-09).
- `ip_do_visitante(request) -> str`: com a trava ligada, o `CF-Connecting-IP` se ele
  existe e é um endereço válido (`ipaddress.ip_address`); senão, e com a trava
  desligada, o `REMOTE_ADDR` (RF-10). O middleware garante que, com a trava ligada, o
  pedido passou pelo proxy, que sobrescreve o `CF-Connecting-IP` a cada pedido.

### `blog_culinario/limitacao.py`

`limite_excedido()` mantém a assinatura e passa a:

```python
ip = ip_do_visitante(request)
cache_key = f"{_PREFIXO_CACHE}:{chave}:{ip}"
cache.add(cache_key, 0, timeout=janela_segundos)
try:
    tentativas = cache.incr(cache_key)
except ValueError:  # a chave expirou entre o add() e o incr()
    cache.add(cache_key, 0, timeout=janela_segundos)
    tentativas = cache.incr(cache_key)
return tentativas > limite
```

Cada pedido recebe um número único do `incr()` atômico, então no máximo `limite`
pedidos passam na janela, mesmo simultâneos (RF-08). Hoje a tentativa recusada não
soma; com o desenho novo, soma, sem efeito visível: o `incr()` não estende a janela, e
a recusa continua até ela acabar.

### `nucleo/views.py` — `servir_midia`

```python
@require_safe
@cache_control(public=True, max_age=86400)
def servir_midia(request: HttpRequest, caminho: str) -> HttpResponseBase:
    try:
        return serve(request, caminho, document_root=settings.MEDIA_ROOT)
    except SuspiciousFileOperation as erro:  # ../ que sai da pasta
        raise Http404 from erro
```

O `serve` junta o caminho ao `MEDIA_ROOT` com `safe_join`, recusa pasta com 404 (sem
`show_indexes`), põe o `Content-Type` pela extensão e responde 304 ao
`If-Modified-Since`. O `SuspiciousFileOperation` do `../` viraria 400 e uma linha de
log; a view o converte em 404, como um arquivo que não existe (RF-07). O `nosniff` vem
do `SecurityMiddleware` (`SECURE_CONTENT_TYPE_NOSNIFF` do `prod.py`). As capas do
projeto são JPEG (o Admin aceita o que o Pillow abre), e o `mimetypes` do Python já as
conhece em qualquer sistema.

### `blog_culinario/urls.py`

```python
path(f"{settings.MEDIA_URL.lstrip('/')}<path:caminho>", servir_midia, name="midia"),
```

No lugar do `if settings.DEBUG: urlpatterns += static(...)`. O docstring do módulo
deixa de dizer que mídia em produção usaria um storage externo.

### `conftest.py`

Fixture `autouse` que aponta o `CACHES["default"]["LOCATION"]` para o `tmp_path` do
teste pela fixture `settings` do `pytest-django`. O sinal `setting_changed` do Django
recria o cache, e cada teste começa com um cache vazio, fora da pasta `django_cache/`
real (RNF-04). Os `cache.clear()` dos testes da spec 006 seguem valendo.

### Documentação

- `.env.example`: `DIRETORIO_DADOS`, `ORIGEM_SEGREDO`, `ORIGEM_SEGREDO_ANTERIOR` (como
  gerar um valor com `secrets.token_urlsafe`), `ALLOWED_HOSTS` com exemplo de
  domínio próprio, e o aviso de que, atrás de proxy sem a trava, todos os visitantes
  dividem o limite de taxa.
- `README.md` e `README.en.md`: seção de deploy com a receita (`railpack.json`), as
  variáveis e a trava de origem; o link da demonstração só com o endereço no ar
  (RNF-06).
- `CLAUDE.md`: visão geral e arquitetura (`cache.py`, `origem.py`, `railpack.json`),
  a nota do piso do Python sem o PythonAnywhere (o piso fica pelo mínimo do Django
  6.1) e uma convenção: view nova que limita por IP usa `limite_excedido()`, nunca o
  `REMOTE_ADDR` direto.
- `docs/stack.md`: Railway, Railpack e gunicorn; SQLite, WhiteNoise e cache revistos
  sem o PythonAnywhere.

## Interfaces

### Variáveis de ambiente (novas ou com uso novo)

| Variável | Padrão | Efeito |
|---|---|---|
| `DIRETORIO_DADOS` | raiz do repositório | Pasta de `db.sqlite3`, `media/` e `django_cache/`; na Railway, o caminho do volume (`/data`) |
| `ORIGEM_SEGREDO` | vazia (trava desligada) | Valor que o cabeçalho `X-Origin-Verify` precisa trazer; ligada, o IP sai do `CF-Connecting-IP` |
| `ORIGEM_SEGREDO_ANTERIOR` | vazia | Segundo valor aceito durante a troca do segredo |
| `ALLOWED_HOSTS` | sem padrão em produção | Agora tolera espaços e vírgula no fim |
| `SECRET_KEY` | sem padrão em nenhum ambiente | Antes `DJANGO_SECRET_KEY`; obrigatória também em desenvolvimento (RF-15) |
| `ADMIN_URL` | `admin/` | Caminho do Admin; vazio ou só barras vale `admin/`, barras sobrando são ignoradas (RF-14) |
| `PORT` | 8000 | Porta do gunicorn; a plataforma define |
| `WEB_CONCURRENCY` | 1 | Workers do gunicorn (lida pelo próprio gunicorn) |

A demonstração roda com `MODO_DEMONSTRACAO=True`, `URL_PUBLICA` e
`ALLOWED_HOSTS` com o domínio próprio, `DIRETORIO_DADOS=/data`,
`ORIGEM_SEGREDO` igual ao da regra do proxy e `SECRET_KEY` própria.

### Cabeçalhos lidos

| Cabeçalho | Quem define | Uso |
|---|---|---|
| `X-Forwarded-Proto` | proxy da plataforma | HTTPS (RF-03) |
| `X-Origin-Verify` | regra de transformação do proxy da Cloudflare, que sobrescreve o valor do cliente | trava de origem (RF-09) |
| `CF-Connecting-IP` | Cloudflare, a cada pedido | IP do visitante, só com a trava ligada (RF-10) |

### Cabeçalhos enviados (novos)

| Cabeçalho | Quem envia | Valor |
|---|---|---|
| `Content-Security-Policy` | `ContentSecurityPolicyMiddleware` do Django, pelo `SECURE_CSP` | a política do `base.py`; no Admin, o `style-src` ganha o nonce do pedido (RF-16) |
| `Permissions-Policy` | `PermissionsPolicyMiddleware` | os oito recursos negados de `PERMISSIONS_POLICY` (RF-17) |

O 403 da trava de origem sai antes dos dois middlewares e vai sem eles: o pedido não
veio pela Cloudflare e não recebe página do blog.

### Rotas

| Rota | Antes | Depois |
|---|---|---|
| `/media/<caminho>` | só com `DEBUG=True` (`static()`) | sempre, pela `servir_midia` (GET e HEAD) |

## ADRs

### ADR-1 — Build e start no `railpack.json`

**Decisão.** Um `railpack.json` na raiz, com os comandos de build e o de start.
**Alternativas.** (a) Dockerfile; (b) `railway.json` com `buildCommand` e
`startCommand`; (c) só o painel da plataforma.
**Porquê.** O Railpack já detecta o Python pelo `.python-version` e o uv pelo
`uv.lock`; o arquivo só fixa os comandos, com esquema validável. O Dockerfile traria
imagem base, instalação do uv e cache de camadas para manter à mão. O painel deixaria a
receita fora do repositório, onde quem clona não a vê. É também a receita do projeto
irmão `portfolio-dinamico`, já no ar.
**Trade-off.** O arquivo só serve ao Railpack. Em outra plataforma, os comandos são os
mesmos, no formato dela.

### ADR-2 — Configurações de produção na linha de comando e no `wsgi.py`

**Decisão.** Cada comando que carrega o Django no `railpack.json` define
`DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod`, e o `wsgi.py` e o `asgi.py`
passam a ter `settings.prod` como padrão.
**Alternativas.** (a) só a variável no painel; (b) `variables` do step e do `deploy` no
`railpack.json`; (c) `manage.py` com `settings.prod` como padrão.
**Porquê.** (a) é o esquecimento que o RF-02 quer impedir: sem a variável, o serviço
subiria com `DEBUG=True` e a chave de desenvolvimento. (b) funciona, mas o Railpack não
documenta qual valor vence quando a variável também está no painel; na linha de
comando, o valor é o da linha. (c) quebraria o `runserver` e o `pytest` de quem clona.
O padrão do `wsgi.py` cobre quem usa outro servidor WSGI sem a receita.
**Trade-off.** O painel não troca mais as configurações do serviço; outro módulo de
configuração exige editar o `railpack.json`.

### ADR-3 — `migrate` no start, antes do gunicorn

**Decisão.** O start roda `migrate --noinput && gunicorn ...`.
**Alternativas.** (a) `migrate` no build; (b) comando de pré-deploy da plataforma.
**Porquê.** O banco mora no volume, que o build não vê: (a) migraria um banco
descartável. No start, a ordem fica num comando só, o mesmo de qualquer servidor, e o
`&&` impede o gunicorn de subir sobre uma migração que falhou. (b) acrescenta um passo
próprio da plataforma, sem ganho numa instância só (RNF-03).
**Trade-off.** Cada reinício roda o `migrate`, que sem migração pendente leva menos de
um segundo.

### ADR-4 — Cache em arquivo com `add()` e `incr()` atômicos

**Decisão.** Um backend do projeto, `CacheArquivoAtomico`, que herda o
`FileBasedCache` e passa o `add()` e o `incr()` por uma trava de arquivo; o `incr()`
preserva a validade da chave.
**Alternativas.** (a) `FileBasedCache` puro; (b) `DatabaseCache` no SQLite; (c) Redis
ou Memcached; (d) `LocMemCache` com um worker só.
**Porquê.** (a) conta errado com pedidos simultâneos e, pior, reinicia a janela a cada
`incr()`. (b) tem a mesma corrida no `add()`/`incr()` e soma escrita a um banco que já
é o gargalo do SQLite. (c) é um serviço a mais para pagar e manter (decisão resolvida
3). (d) amarra o desempenho a um processo e quebra no dia em que `WEB_CONCURRENCY`
subir. A trava de arquivo vale entre processos no Linux e no Windows.
**Trade-off.** O `incr()` lê o formato do arquivo do `FileBasedCache` (validade e
valor), que é interno do Django: um teste confere a validade preservada e acusa se uma
versão nova mudar o formato. Uma trava única serializa todas as contagens, o que só
pesaria com muito mais tráfego do que uma demonstração tem.

### ADR-5 — Trava de origem por segredo compartilhado, desligada sem a variável

**Decisão.** Um middleware compara o `X-Origin-Verify` com `ORIGEM_SEGREDO` (ou o
anterior) e recusa com 403; sem a variável, não faz nada. O `CF-Connecting-IP` só é
lido com a trava ligada.
**Alternativas.** (a) confiar no `CF-Connecting-IP` sempre; (b) IP mais à direita do
`X-Forwarded-For`; (c) restringir a origem às faixas de IP da Cloudflare; (d) falhar
fechado sem a variável.
**Porquê.** (a) deixa qualquer cliente que alcance o serviço sem o proxy escolher o
próprio IP e escapar do limite. (b) depende de quantos proxies há na frente, o que
muda entre plataformas. (c) não serve na Railway, que não deixa restringir a origem por
IP, e a lista de faixas muda. (d) derrubaria todo deploy de quem clona sem Cloudflare
(decisão resolvida 5).
**Trade-off.** Um deploy atrás de proxy sem a trava divide o limite entre todos os
visitantes; fica documentado no `.env.example` e nos READMEs.

### ADR-6 — Mídia pelo `serve` do Django, atrás de uma view fina

**Decisão.** A `servir_midia` chama o `django.views.static.serve` com
`Cache-Control: public, max-age=86400`, com e sem `DEBUG`.
**Alternativas.** (a) WhiteNoise; (b) bucket (S3, R2) com `django-storages`; (c)
servidor web na frente.
**Porquê.** (a) indexa os arquivos quando o processo sobe, e a capa nova enviada pelo
Admin só apareceria no reinício seguinte. (b) traz dependência, credencial e cobrança
para uma demonstração com poucas imagens (não-objetivos). (c) não existe na
plataforma. A Cloudflare guarda as imagens em cache pela extensão, então o Django
serve cada arquivo poucas vezes.
**Trade-off.** A documentação do Django desaconselha o `serve` em produção, por
eficiência e por não ter passado por auditoria de segurança. Aqui o tráfego é baixo, o
envio é só pelo Admin (o `ImageField` passa pelo Pillow, que recusa o que não é
imagem) e o `nosniff` vale nas respostas. O `max-age` de um dia não esconde troca de
capa: o Django gera nome novo quando o arquivo já existe.

### ADR-7 — Erros na saída de erro, sem o 404

**Decisão.** `LOGGING` com um `StreamHandler` na raiz (WARNING) e o `django.request` em
ERROR, só no `prod.py`.
**Alternativas.** (a) `ADMINS` e o erro por e-mail; (b) serviço de monitoramento
(Sentry).
**Porquê.** A plataforma já guarda o `stdout` e o `stderr` de cada deploy; (a) exigiria
e-mail, que o blog não envia (decisão resolvida 8), e (b) traria dependência e conta. O
404 fica fora porque robôs testam caminhos o dia inteiro e afogariam o erro real.
**Trade-off.** O aviso de `Host` inválido (`django.security.DisallowedHost`), a falha
de CSRF e o aviso da trava de origem continuam no log; com o endereço da plataforma
fora do ar (decisão resolvida 7), são raros.

### ADR-8 — `mail.E001` silenciado, sem servidor de e-mail

**Decisão.** `SILENCED_SYSTEM_CHECKS = ["mail.E001"]` no `prod.py`, com o comentário
que diz quando tirar.
**Alternativas.** (a) SMTP no `prod.py` sem servidor configurado; (b) tirar o
`MAILERS` e cair no padrão do Django (SMTP).
**Porquê.** Nenhuma funcionalidade envia e-mail (decisão resolvida 8). (a) e (b)
fariam a checagem passar fingindo um envio que não existe, e um e-mail futuro falharia
contra um servidor que não há, em vez de ficar visível no código.
**Trade-off.** Se uma funcionalidade nova passar a enviar e-mail, o `check --deploy`
não avisa; o comentário do `prod.py` e a convenção do `CLAUDE.md` apontam a linha.

### ADR-9 — `ADMIN_URL` normalizado no `base.py`

**Decisão.** `ADMIN_URL = (env.str("ADMIN_URL", default="").strip().strip("/") or
"admin") + "/"` no `base.py`, e `path(settings.ADMIN_URL, admin.site.urls)` no
`urls.py`. O `robots.txt` vira `User-agent: *` / `Allow: /` (spec 010, decisão
resolvida 6). Testes e links do Admin usam `reverse("admin:...")`.
**Alternativas.** (a) Ler o valor cru, sem normalização; (b) recusar na subida o
valor sem barra no fim.
**Porquê.** Com (a), o vazio põe o Admin na raiz e `painel` sem barra gera
`painellogin/`. (b) derruba um deploy por um detalhe que tem conserto óbvio; normalizar
aceita as formas comuns e não deixa caminho quebrado.
**Trade-off.** Um caminho com barra no meio (`a/b/`) passa como está; não há motivo
para recusá-lo.

### ADR-10 — `SECRET_KEY` sem default em todo ambiente

**Decisão.** `SECRET_KEY = env.str("SECRET_KEY")` no `base.py`, sem default; o
`prod.py` deixa de redefini-la. O `ci.yml` e o `lighthouse.yml` definem um placeholder
no `env` do job.
**Alternativas.** (a) Manter a chave fixa no `base.py` só para o desenvolvimento;
(b) gerar uma chave aleatória a cada subida em desenvolvimento.
**Porquê.** (a) deixa uma chave conhecida no repositório; (b) derruba as sessões a
cada reinício do `runserver`. Gerar uma vez no `.env` é um passo só e não deixa
chave fixa no código.
**Trade-off.** Quem clona tem um passo a mais antes do `runserver` (README).

### ADR-11 — CSP nativa do Django, com nonce só no estilo

**Decisão.** `SECURE_CSP` no `base.py`, com o middleware e o context processor do
próprio Django 6; `CSP.NONCE` só no `style-src`. O `Permissions-Policy` sai de um
middleware do projeto (`cabecalhos.py`).
**Alternativas.** (a) O pacote `django-csp`; (b) `'unsafe-inline'` no
`style-src`; (c) a CSP só no `prod.py`; (d) nonce também no
`script-src`.
**Porquê.** (a) é uma dependência a mais para o que o Django já faz, e o Admin do
Django 6 marca as próprias tags com o nonce da política nativa. (b) abriria o estilo
inline para todo o site por causa de um `<style>` do Admin, que o nonce já resolve.
(c) deixaria o desenvolvimento e o Lighthouse CI sem a política, e um template com
script inline só falharia no ar; as páginas de depuração já saem da política
sozinhas. (d) não acrescenta nada: o Admin não tem script inline, e sem o nonce no
`script-src` um script injetado não roda nem copiando o nonce de uma tag vizinha.
**Trade-off.** No Admin, o cabeçalho muda a cada pedido (o nonce). Uma página nova
com estilo inline precisa do `{% csp_nonce_attr %}`; com script inline, de um
arquivo em `static/js/`.

## Impacto no código existente

- **Dependências:** o extra `prod` ganha o `gunicorn`. A versão sai do lock com o
  cooldown de 7 dias do projeto: o 27.0.1 (12/11/2026) e o 27.0.0 (10/11/2026) ainda
  estão dentro dele, então o piso é o 26.2.0 até o cooldown passar.
- **Limitação de taxa (spec 006):** o comportamento observável é o mesmo (limites,
  janelas e mensagens). Mudam o IP, que pode vir do `CF-Connecting-IP`, e o backend do
  cache. A spec 006 fica como está (registro concluído), e o RF-03 dela (janela que
  expira sozinha) passa a ser garantido também no cache em arquivo.
- **Testes existentes:** passam a rodar com o cache em arquivo numa pasta temporária
  (`conftest.py`); os de limitação de taxa seguem com `REMOTE_ADDR`, porque a trava
  fica desligada nos testes.
- **Desenvolvimento:** sem `DIRETORIO_DADOS`, banco e mídia não mudam de lugar; o cache
  passa a criar `django_cache/` na raiz (no `.gitignore`), e a mídia sai com
  `Cache-Control` também no `runserver`.
- **CI e Lighthouse CI:** ganham a `SECRET_KEY` placeholder (ADR-10); fora isso,
  nada muda. O Lighthouse CI sobe o `runserver` com as
  configurações de desenvolvimento e sem `ORIGEM_SEGREDO`.
- **Specs concluídas** que citam o PythonAnywhere ficam como estão (não-objetivos).
- **Cabeçalhos (ADR-11):** toda resposta passa a levar a CSP e o
  `Permissions-Policy`, também no `runserver` e no Lighthouse CI, que já reprova
  erro de console: uma violação da CSP numa página pública aparece lá.

## Estratégia de testes

Tudo em `nucleo/test_hospedagem.py`, sem rede e sem tocar a pasta de dados real,
menos os cabeçalhos de segurança, em `nucleo/test_cabecalhos.py` (o último item).

- **Configurações de produção num processo à parte:** um helper roda
  `python -c` num `subprocess` com o ambiente pedido (`DJANGO_SETTINGS_MODULE`,
  `SECRET_KEY`, `ALLOWED_HOSTS`, `DIRETORIO_DADOS` num `tmp_path`) e
  devolve os valores lidos em JSON. Recarregar o pacote de configurações dentro do
  processo do pytest deixaria o `base.py` com o ambiente de um teste para os outros.
  Cobre `ALLOWED_HOSTS` com espaços, vírgula no fim e vazia, e a subida que falha sem
  ela (RF-05); `DIRETORIO_DADOS` ausente, absoluto e relativo, com os caminhos do
  banco, da mídia e do cache (RF-06); `SECURE_PROXY_SSL_HEADER`, `LOGGING` e
  `SILENCED_SYSTEM_CHECKS` presentes em produção e ausentes em desenvolvimento; o
  `wsgi.py` sem `DJANGO_SETTINGS_MODULE` carregando `settings.prod` (RF-02); e
  `manage.py check --deploy` com código de saída 0 e só o `security.W021` na saída
  (RF-12).
- **Receita de build:** lê o `railpack.json` como JSON e confere `--locked`,
  `--no-dev`, `--extra prod`, o `collectstatic` com `settings.prod`, o `migrate` antes
  do `gunicorn`, `settings.prod` no start e `${PORT:-8000}` (RF-01, RF-02).
- **Proxy e CSRF:** `override_settings` liga `SECURE_SSL_REDIRECT`, os cookies seguros
  e o `SECURE_PROXY_SSL_HEADER`, com um domínio de exemplo em `ALLOWED_HOSTS` e no
  `HTTP_HOST`. GET com `HTTP_X_FORWARDED_PROTO="https"`: 200 e `csrftoken` com `secure`;
  sem ele: 301. POST do login com `Client(enforce_csrf_checks=True)`, token do cookie e
  `HTTP_ORIGIN` do mesmo domínio: passa pelo CSRF; com `HTTP_ORIGIN` de outro site: 403
  (RF-03, RF-04).
- **Mídia:** `MEDIA_ROOT` no `tmp_path`, com um JPEG e uma subpasta, e `DEBUG=False`.
  Arquivo: 200, `Content-Type: image/jpeg`, `nosniff`, `Cache-Control` com
  `max-age=86400`; inexistente, pasta e `../`: 404 com o `404.html`; POST: 405 (RF-07).
- **Cache:** duas instâncias do `CacheArquivoAtomico` na mesma pasta (o que dois
  workers têm) e um `subprocess` que soma na mesma pasta: a contagem de um aparece no
  outro. Threads que chamam `limite_excedido()` ao mesmo tempo, cada uma com a sua
  instância: no máximo `limite` aceitas. O `incr()` preserva a validade (a chave expira
  no fim da janela original) e levanta `ValueError` em chave ausente ou expirada
  (RF-08).
- **Trava de origem:** `override_settings(ORIGEM_SEGREDOS=…)`: sem segredo, 200; com
  segredo, 403 com o `403.html` sem o cabeçalho e com valor errado, 200 com o atual e
  com o anterior. `caplog`: uma linha de aviso com método e caminho, sem o valor
  recebido (RF-09, RF-11, RNF-05).
- **IP:** `ip_do_visitante()` com `RequestFactory`: `CF-Connecting-IP` com a trava
  ligada, `REMOTE_ADDR` com ela desligada ou com cabeçalho ausente ou inválido (RF-10).
- **Log:** o `override_settings` não reconfigura o `logging`, então o teste aplica o
  `LOGGING` lido do `prod.py` com `logging.config.dictConfig` num `subprocess`, emite
  um ERROR e um WARNING no `django.request` e confere o `stderr`: o ERROR sai, o WARNING
  (o nível do 404) não (RF-11).
- **Cabeçalhos:** o client de teste pede as páginas públicas (com uma receita criada)
  e lê a CSP diretiva por diretiva na resposta, não no settings: um nome de
  configuração errado tiraria o cabeçalho sem acusar. O HTML público não tem
  `<script>` sem `src`, `<style>`, `style=` nem atributo de evento. No Admin, com um
  superusuário, o `style-src` traz o nonce, todo `<style>` inline traz o mesmo
  nonce e não há script inline. O `Permissions-Policy` é o valor de
  `PERMISSIONS_POLICY` (RF-16, RF-17, RNF-02).

## Desvios

1. **Cache da suíte (RNF-04, componente `conftest.py`):** a fixture automática não
   bastava. A coleta do pytest já abre o cache (ela inspeciona o `cache` que os módulos
   de teste importam do Django), e a criação do banco de teste roda o
   `createcachetable`; os dois aconteciam antes de qualquer fixture e criavam a
   `django_cache/` da raiz. O `conftest.py` ganhou um `pytest_configure` que liga, antes
   da coleta, um `override_settings` com o cache numa pasta temporária da sessão, e o
   `pytest_unconfigure` o desliga e apaga a pasta. A fixture por teste segue valendo.
2. **Chave secreta obrigatória em produção (RF-02):** o RF-02 supunha que o `prod.py`
   já falhava sem `SECRET_KEY`, mas ele herdava do `base.py` a chave insegura de
   desenvolvimento e subia com ela. O `prod.py` passou a ler a variável sem default:
   ausente, a subida falha; vazia, o Django recusa a chave. Dois testes guardam isso.
3. **`DJANGO_DEBUG` removida (RNF-06):** a variável não tinha efeito: o `dev.py`
   força `DEBUG=True` e o `prod.py`, `False`. O `base.py` fixa `DEBUG = False`, e a
   variável saiu do `.env.example`.
4. **`.env.example` reescrito (RNF-06):** além das variáveis novas, o arquivo ganhou
   cabeçalho que explica para que serve e como usar, seções numeradas e, em cada
   variável, o formato, se é pública ou segredo e o que acontece vazia. O `.gitignore`
   passou a ignorar `.env.*` e a trazer de volta o `.env.example` com `!.env.example`.
5. **Comparação do segredo de origem (RNF-05, ADR-5):** o middleware compara o
   cabeçalho com todos os segredos aceitos, sem parar no primeiro acerto, para o tempo
   de resposta não variar com a posição do segredo.
6. **Capa em WebP com o tipo certo (RF-07):** no ar, as capas saíam com
   `Content-Type: application/octet-stream`. O Python 3.12 só conhece o `.webp` pelo
   `mime.types` do sistema, que o contêiner da plataforma não tem (o tipo entrou no
   `mimetypes` no 3.13), e o `serve` escolhe o tipo pela extensão. O `nucleo/views.py`
   registra `image/webp` com `mimetypes.add_type`, e um teste guarda o tipo (PR #69).

## Notas de implementação

- **Suíte:** 322 testes ao fim da spec, com as Etapas 6b e 6c e a correção do WebP.
- **`check --deploy`:** no ar, só o `security.W021` (`SECURE_HSTS_PRELOAD` desligado,
  de propósito enquanto o HSTS é de 7 dias) e o `mail.E001` silenciado (o blog não
  envia e-mail).
- **Console da plataforma:** o shell não carrega o ambiente do start, então o
  `python` não está no `PATH`; o ambiente virtual do build fica em `/app/.venv`
  (`export PATH="/app/.venv/bin:$PATH"`). A `DJANGO_SETTINGS_MODULE` também fica
  nas variáveis do serviço, porque o Console não passa pelo `export` do start.
- **Conteúdo inicial:** levado do ambiente local para o volume com `dumpdata
  --natural-foreign --natural-primary` (os usuários entram pelo nome e não colidem
  com o superusuário criado em produção) e `loaddata`; a autora das receitas entra
  sem senha utilizável.
- **Cache da Cloudflare:** a mídia sai com `Cache-Control: public, max-age=86400`, e a
  Cloudflare guarda `.webp` por padrão. Uma resposta corrigida na origem só aparece
  de fora depois de um purge das URLs (ou de um dia).
- **No ar:** conferido de fora: redirect 301 de HTTP para HTTPS, HSTS, `nosniff`,
  `X-Frame-Options`, `Content-Security-Policy`, `Permissions-Policy`, cookie CSRF
  com `Secure`, `/admin/` padrão em 404, a capa em `image/webp`, `../` em 404, o
  login com a conta de demonstração, o POST com `Origin` de outro site em 403, a
  sexta senha errada recusada e o pedido direto à plataforma, sem passar pelo proxy,
  sem resposta do site. No log do deploy, o `migrate` roda antes do gunicorn, que
  escuta na `PORT` da plataforma (RF-01, RF-03, RF-04, RF-07, RF-08, RF-10, RF-16,
  RF-17).

