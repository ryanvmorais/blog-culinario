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

# 011 — Hospedagem da demonstração na Railway

## Contexto e problema

O blog não tem mais destino de deploy: a documentação ainda cita o PythonAnywhere,
que deixou de ser o alvo. A instância pública de demonstração (specs 009 e 010) vai
ficar na Railway, em `https://blog-culinario.ryanmorais.com.br`, com o domínio
passando pelo proxy da Cloudflare.

O código de hoje supõe um servidor que entrega o pedido direto ao Django, com um
processo só. Na Railway, atrás da Cloudflare, várias suposições deixam de valer:

- **HTTPS:** o TLS termina no proxy, e o Django recebe HTTP. Com `DEBUG=False`, o
  `SECURE_SSL_REDIRECT` redireciona todo pedido para HTTPS, e o pedido redirecionado
  chega de novo como HTTP: o site entra em laço de redirect.
- **Disco:** o sistema de arquivos do contêiner é recriado a cada deploy. O
  `db.sqlite3` e a pasta `media/` (capas das receitas enviadas pelo Admin) ficam na
  raiz do repositório e somem no deploy seguinte.
- **Mídia:** com `DEBUG=False`, a rota de `/media/` não existe (`blog_culinario/urls.py`),
  e as capas respondem 404.
- **Limitação de taxa (spec 006):** o contador usa o cache padrão, um `LocMemCache`
  que vive dentro de cada processo. Com mais de um worker do gunicorn, cada worker
  conta separado, e o limite se multiplica pelo número de workers. E o IP vem do
  `REMOTE_ADDR`, que atrás do proxy é o endereço do próprio proxy: todos os
  visitantes dividem o mesmo contador. Na demonstração, a conta pública `visitante`
  (spec 009) fica no login, e cinco senhas erradas de qualquer pessoa bloqueariam o
  login de todo mundo por cinco minutos.
- **Erros invisíveis:** com `DEBUG=False`, o Django só manda o traceback de um erro
  500 por e-mail aos `ADMINS`, que o projeto não define. Nada aparece no log da
  plataforma.
- **`check --deploy` falha:** o Django 6.1 trata o backend de e-mail de console como
  só de desenvolvimento (`mail.E001`). O blog não envia e-mail, mas o erro impede usar
  o `check --deploy` como conferência.

Também não há, no repositório, a receita de build e de start, nem o gunicorn entre
as dependências. E o `wsgi.py` cai nas configurações de desenvolvimento quando
`DJANGO_SETTINGS_MODULE` não está definida.

## Objetivos

- Deixar no repositório tudo o que a Railway precisa para construir e iniciar o
  projeto a cada push na `main`, sempre com as configurações de produção.
- Fazer o HTTPS, o CSRF, os cookies seguros e o HSTS funcionarem atrás do proxy.
- Guardar banco, mídia e cache num diretório configurável, que a plataforma monta
  como volume e que sobrevive ao deploy.
- Servir as capas enviadas pelo Admin com `DEBUG=False`.
- Manter a limitação de taxa por visitante: um contador só para todos os workers e
  o IP real do visitante quando o pedido comprovadamente passou pela Cloudflare.
- Deixar os erros do servidor visíveis no log da plataforma.
- `check --deploy` sem erro.
- Dar às variáveis o nome da própria configuração do Django (`SECRET_KEY`,
  `ALLOWED_HOSTS`), tornar configurável o caminho do Admin (`ADMIN_URL`) e exigir a
  chave secreta em todo ambiente.
- Tirar o PythonAnywhere da documentação e pôr no lugar a hospedagem nova.

## Não-objetivos

- **Guia de painel passo a passo.** O repositório traz a receita de build e as
  variáveis de ambiente; criar o serviço, o volume, o domínio e a regra do proxy é
  feito no painel de cada plataforma.
- **PostgreSQL ou `DATABASE_URL`.** O SQLite segue sendo o banco do projeto.
- **Armazenamento de objetos para a mídia** (S3, R2): o volume atende ao tamanho da
  demonstração.
- **Mais de uma réplica, deploy sem queda e healthcheck.** Com volume, a troca de
  versão tem uma janela curta fora do ar.
- **Envio de e-mail** (SMTP, redefinição de senha por e-mail): o blog não envia
  e-mail.
- **Subir o piso do Python** (`requires-python`, `.python-version`, matriz do CI).
- **Carregar o conteúdo da demonstração** (receitas, capas, superusuário, conta
  `visitante`): é operação de dados, fora do código.
- **Mudar as specs concluídas** que citam o PythonAnywhere: ficam como registro do
  que valia quando foram escritas.

## Personas

- Como **visitante da demonstração**, quero abrir o blog pelo link do README, ver as
  capas e entrar com a conta pública, para conhecer o projeto antes de clonar.
- Como **quem clona e publica o blog**, quero a receita de build e as variáveis
  documentadas, para o deploy funcionar sem editar as configurações, com ou sem
  Cloudflare na frente.
- Como **quem mantém a demonstração**, quero que banco e capas sobrevivam ao deploy e
  que os erros apareçam no log, para cada push na `main` não apagar o conteúdo nem
  esconder uma falha.
- Como **aprendiz de Django**, quero ver no código como uma aplicação roda atrás de
  um proxy: HTTPS, IP do visitante, mídia e cache entre processos.

## Requisitos funcionais

### Build e start

### RF-01 — Build e start declarados no repositório

- **Given** um push na `main`
  **When** a Railway constrói o projeto
  **Then** as dependências vêm do `uv.lock` (sem as ferramentas de dev, com o extra
  `prod`, que traz o gunicorn) e o `collectstatic` roda no build.
- **Given** um `uv.lock` que não bate com o `pyproject.toml`
  **When** a Railway constrói o projeto
  **Then** o build falha em vez de resolver as versões de novo.
- **Given** o build concluído
  **When** o serviço inicia
  **Then** o `migrate` roda antes do servidor, e o gunicorn escuta na porta da
  variável `PORT` (8000 se ela faltar).

### RF-02 — O serviço sobe sempre com as configurações de produção

- **Given** o serviço iniciado pela receita do RF-01, sem `DJANGO_SETTINGS_MODULE`
  definida no ambiente
  **When** o `migrate` e o gunicorn carregam o projeto
  **Then** os dois usam `blog_culinario.settings.prod`, nunca as de desenvolvimento.
- **Given** as configurações de produção sem `SECRET_KEY` ou sem
  `ALLOWED_HOSTS`
  **When** o serviço inicia
  **Then** a subida falha (a chave, em qualquer ambiente: RF-15).
- **Given** o desenvolvimento local
  **When** o `manage.py` roda sem `DJANGO_SETTINGS_MODULE`
  **Then** segue usando `blog_culinario.settings.dev`, como hoje.

### Atrás do proxy

### RF-03 — HTTPS reconhecido atrás do proxy

- **Given** as configurações de produção e um pedido com `X-Forwarded-Proto: https`
  **When** o Django responde
  **Then** não há redirect para HTTPS, o pedido conta como seguro e os cookies de
  sessão e de CSRF saem com `Secure`.
- **Given** as configurações de produção e um pedido sem esse cabeçalho, ou com
  `http`
  **When** o Django responde
  **Then** a resposta é o redirect 301 para HTTPS, como hoje.
- **Given** o desenvolvimento local
  **When** o `runserver` atende um pedido HTTP
  **Then** nada muda.

### RF-04 — Formulários e Admin aceitam POST pelo domínio público

- **Given** as configurações de produção, o host em `ALLOWED_HOSTS` e um
  pedido HTTPS pelo proxy
  **When** o login, o cadastro, o comentário ou o login do Admin é enviado com o
  token CSRF e `Origin` igual ao endereço do site
  **Then** o pedido passa pela verificação de CSRF.
- **Given** o mesmo cenário com `Origin` de outro site
  **When** o pedido chega
  **Then** a resposta é 403, com a página de erro do CSRF.

### RF-05 — `ALLOWED_HOSTS` tolera espaços e vírgula sobrando

- **Given** `ALLOWED_HOSTS=exemplo.com, www.exemplo.com,`
  **When** as configurações de produção carregam
  **Then** a lista fica `["exemplo.com", "www.exemplo.com"]`.
- **Given** `ALLOWED_HOSTS` vazia
  **When** as configurações de produção carregam
  **Then** todo host é recusado (falha fechada); ausente, a subida falha (RF-02).

### Dados persistentes

### RF-06 — Banco, mídia e cache num diretório configurável

- **Given** um ambiente sem `DIRETORIO_DADOS`
  **When** o projeto sobe
  **Then** o banco e a mídia ficam onde estão hoje (`db.sqlite3` e `media/` na raiz
  do repositório), e o cache em `django_cache/`, também na raiz.
- **Given** `DIRETORIO_DADOS=/data`
  **When** o projeto sobe
  **Then** o banco fica em `/data/db.sqlite3`, a mídia em `/data/media/` e o cache em
  `/data/django_cache/`.
- **Given** o diretório montado como volume e um deploy novo
  **When** o serviço reinicia
  **Then** as receitas, os comentários, as contas e as capas continuam lá.

### RF-07 — Mídia servida com `DEBUG=False`

- **Given** `DEBUG=False` e uma capa enviada pelo Admin
  **When** o navegador pede `/media/<caminho>`
  **Then** a resposta é 200 com o `Content-Type` do arquivo e o cabeçalho
  `X-Content-Type-Options: nosniff`.
- **Given** `DEBUG=False` e um caminho que não existe, uma pasta ou um caminho que
  sai da pasta de mídia (`../`)
  **When** o navegador pede o endereço
  **Then** a resposta é 404, com a página `404.html`, sem listar arquivos.
- **Given** `DEBUG=True`
  **When** o navegador pede `/media/<caminho>`
  **Then** o comportamento é o de hoje.

### Limitação de taxa por visitante

### RF-08 — Um contador só para todos os workers

- **Given** o gunicorn com mais de um worker
  **When** o mesmo IP faz cinco tentativas de login erradas, atendidas por workers
  diferentes
  **Then** a sexta tentativa na janela é recusada, qualquer que seja o worker, com a
  mensagem de hoje (spec 006).
- **Given** tentativas simultâneas do mesmo IP
  **When** chegam ao mesmo tempo em workers diferentes
  **Then** o número de tentativas aceitas na janela não passa do limite.
- **Given** o comentário (spec 006, RF-02)
  **When** é limitado
  **Then** vale o mesmo contador compartilhado.

### RF-09 — Trava de origem opcional

- **Given** `ORIGEM_SEGREDO` definida
  **When** chega um pedido sem o cabeçalho `X-Origin-Verify` ou com valor diferente
  **Then** a resposta é 403, com a página `403.html`, antes de qualquer view.
- **Given** `ORIGEM_SEGREDO` definida
  **When** chega um pedido com `X-Origin-Verify` igual a ela
  **Then** o pedido segue normalmente.
- **Given** `ORIGEM_SEGREDO` e `ORIGEM_SEGREDO_ANTERIOR` definidas (troca do segredo)
  **When** chega um pedido com o valor de qualquer uma das duas
  **Then** o pedido segue normalmente.
- **Given** `ORIGEM_SEGREDO` vazia ou ausente (o padrão)
  **When** chega um pedido
  **Then** a trava fica desligada e nada muda.

### RF-10 — IP do visitante

- **Given** a trava de origem ligada e um pedido que passou por ela
  **When** a limitação de taxa identifica o visitante
  **Then** usa o `CF-Connecting-IP`, e o `REMOTE_ADDR` se o cabeçalho faltar.
- **Given** a trava de origem desligada
  **When** a limitação de taxa identifica o visitante
  **Then** usa o `REMOTE_ADDR`, e um `CF-Connecting-IP` enviado pelo cliente é
  ignorado.

### Operação

### RF-11 — Erros aparecem no log do serviço

- **Given** `DEBUG=False` e uma exceção não tratada numa view
  **When** o Django responde 500
  **Then** o traceback sai na saída de erro do processo, que a plataforma mostra no
  log do serviço.
- **Given** `DEBUG=False` e um pedido para um endereço que não existe
  **When** o Django responde 404
  **Then** nada sai no log.
- **Given** a trava de origem ligada e um pedido recusado por ela
  **When** a resposta é 403
  **Then** uma linha de aviso sai no log com o método e o caminho, sem o valor do
  cabeçalho recebido.

### RF-12 — `check --deploy` sem erro

- **Given** as configurações de produção com as variáveis obrigatórias
  **When** `uv run python manage.py check --deploy` roda
  **Then** não há erro, e o único aviso é o `security.W021` (HSTS preload desligado),
  que já existe hoje.

### Admin e chave secreta

### RF-14 — Caminho do Admin configurável

- **Given** `ADMIN_URL=painel-secreto/`
  **When** o site sobe
  **Then** o Admin responde em `/painel-secreto/`, e `/admin/` não é mais o painel.
- **Given** `ADMIN_URL` ausente, vazia ou só com barras
  **When** o site sobe
  **Then** o Admin fica em `/admin/`; nunca na raiz, no lugar da home.
- **Given** `ADMIN_URL` com barra sobrando ou faltando (`/painel-secreto`)
  **When** o site sobe
  **Then** o caminho fica `painel-secreto/`.
- **Given** qualquer `ADMIN_URL`
  **When** `/robots.txt` é pedido
  **Then** o arquivo não cita o caminho (spec 010, RF-04).

### RF-15 — Chave secreta obrigatória em todo ambiente

- **Given** as configurações de desenvolvimento ou de produção sem `SECRET_KEY`
  **When** o projeto carrega
  **Then** a subida falha; vazia, o Django recusa a chave. Não há chave fixa no
  repositório.
- **Given** o CI e o Lighthouse CI
  **When** a suíte ou o servidor sobem
  **Then** usam uma `SECRET_KEY` descartável definida no workflow.

### Cabeçalhos de segurança

### RF-16 — Content-Security-Policy em toda resposta

- **Given** qualquer página pública (home, receitas, entrar, cadastro, 404)
  **When** a resposta sai
  **Then** traz o `Content-Security-Policy` com script, estilo, imagem e fonte só do
  próprio site, `base-uri` e `object-src` em `'none'`, `form-action` em `'self'` e
  `frame-ancestors` em `'none'`; sem nonce, porque nada é inline.
- **Given** uma página do Admin
  **When** a resposta sai
  **Then** o `style-src` aceita também o nonce do pedido, que o Admin põe no `<style>`
  inline dele; o `script-src` segue só `'self'`.
- **Given** as configurações de desenvolvimento ou de produção
  **When** o site sobe
  **Then** a política é a mesma; as páginas de depuração do Django (`DEBUG=True`)
  ficam de fora sozinhas.

### RF-17 — Permissions-Policy em toda resposta

- **Given** qualquer resposta
  **When** ela sai
  **Then** traz o `Permissions-Policy` com acelerômetro, câmera, localização,
  giroscópio, magnetômetro, microfone, pagamento e USB negados; uma view que defina o cabeçalho mantém o valor dela.

## Requisitos não-funcionais

### RNF-01 — Só o gunicorn de dependência nova

O `pyproject.toml` ganha o extra `prod` com o gunicorn e nenhuma outra dependência
de runtime. A trava de origem, a escolha do IP, a mídia e o cache usam só o Django.

### RNF-02 — Postura de segurança mantida

O HSTS, o `X-Frame-Options`, o `nosniff` e os cookies seguros de `settings/prod.py`
seguem iguais. Nenhum template ganha `<script>` ou estilo inline: a CSP do RF-16
bloquearia, e a suíte confere o HTML das páginas públicas.

### RNF-03 — Uma instância

O SQLite e o cache em arquivo vivem no mesmo volume, que só uma instância monta. O
desenho supõe uma réplica do serviço; o gunicorn pode ter mais de um worker, porque o
cache em arquivo é compartilhado entre processos (RF-08).

### RNF-04 — Desenvolvimento local, CI e Lighthouse CI inalterados

Sem as variáveis novas, o `runserver`, o `uv run pytest`, o CI e o Lighthouse CI se
comportam como hoje: mesmos caminhos, mesmas respostas e as mesmas notas. A suíte não
grava na pasta de dados real. A exceção é a `SECRET_KEY` (RF-15): quem clona gera uma
no `.env`, e os workflows definem um placeholder.

### RNF-05 — Segredo fora do log e das respostas

O valor de `ORIGEM_SEGREDO`, de `ORIGEM_SEGREDO_ANTERIOR` e do cabeçalho recebido
nunca aparece no log, numa página de erro nem numa resposta. A comparação com o
segredo leva o mesmo tempo para qualquer valor recebido.

### RNF-06 — Documentado para quem clona

O `.env.example`, os dois READMEs (no mesmo PR, com as mesmas seções), o `CLAUDE.md`
e o `docs/stack.md` descrevem as variáveis novas, a receita de build, a trava de
origem e o que acontece com a limitação de taxa atrás de um proxy sem ela. Nenhum
arquivo fora de `specs/` concluídas cita o PythonAnywhere. O link da demonstração
entra nos dois READMEs só depois de o endereço responder com o conteúdo carregado.

## Perguntas em aberto

Nenhuma.

## Decisões resolvidas

1. **Railway como plataforma** (2026-11-01). Deploy a cada push na `main`, cobrança
   por uso, domínio próprio sem trocar de plano e Python na versão do
   `.python-version`.
2. **SQLite, mídia e cache num volume** (2026-11-01). O projeto usa SQLite de
   propósito (spec 000), e o volume guarda os três num lugar só, sem banco gerenciado
   nem bucket.
3. **Cache em arquivo no volume, não outro serviço** (2026-11-16). Um Redis ou um
   Memcached seria um serviço a mais para pagar e manter numa demonstração; o cache
   em arquivo é do próprio Django e se divide entre os workers. O que falta a ele (a
   reserva e a contagem não são atômicas entre processos) o RF-08 cobre.
4. **IP real pelo `CF-Connecting-IP`, só com a trava de origem** (2026-11-01). A
   Cloudflare sobrescreve esse cabeçalho a cada pedido, mas um cliente que alcance o
   serviço por outro caminho pode inventá-lo; a trava de origem garante que o pedido
   passou pela Cloudflare. O login segue limitado no modo demonstração (spec 009), e
   sem o IP real a conta pública seria bloqueada para todos por qualquer pessoa. O
   cabeçalho `X-Origin-Verify` é o que uma regra de transformação do proxy acrescenta
   a todo pedido, sobrescrevendo o que o visitante enviar.
5. **A trava de origem é opcional** (2026-11-16). Sem `ORIGEM_SEGREDO`, o blog roda
   como hoje: quem clona e publica sem Cloudflare não precisa de nada. Falhar fechado
   quando a variável falta foi descartado, porque derrubaria todo deploy que não usa
   a Cloudflare. O custo: um deploy atrás de proxy sem a trava divide o limite entre
   todos os visitantes, e isso fica documentado (RNF-06).
6. **Dois segredos aceitos durante a troca** (2026-11-16). Trocar o segredo no proxy
   e no serviço ao mesmo tempo não é possível; aceitar o atual e o anterior por um
   tempo evita a janela de 403.
7. **Só o domínio próprio fica público.** O endereço gerado pela plataforma não é
   publicado: a demonstração tem um endereço só, o de `URL_PUBLICA` (spec 010).
8. **Sem e-mail** (2026-11-15). Nenhuma funcionalidade do blog envia e-mail, e o modo
   demonstração não pede credencial de SMTP. O `mail.E001` se resolve sem configurar
   um servidor de e-mail.
9. **O PythonAnywhere sai da documentação** (2026-11-16). Renovação manual a cada 30
   dias no plano gratuito e configuração manual do servidor pesam para quem está
   começando. As specs concluídas que o citam ficam como estão (não-objetivos).
10. **Variáveis com o nome do Django e Admin configurável** (2026-11-16).
    `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` passam a `SECRET_KEY` e
    `ALLOWED_HOSTS`, o nome da própria configuração do Django, que dispensa traduzir
    um nome no outro; o Admin ganha o `ADMIN_URL` (RF-14), com o vazio valendo
    `admin/`. A proteção do Admin é o caminho trocado mais a senha; um limite próprio
    no login do Admin foi descartado.
11. **Sem chave fixa nem em desenvolvimento** (2026-11-16). A chave insegura do
    `base.py` valia em todo clone e podia chegar a um deploy que não usasse o
    `prod.py`. Gerar a chave vira um passo do "Como rodar", e o CI define um
    placeholder (RF-15).
12. **CSP nativa do Django e Permissions-Policy por middleware** (2026-11-16). A CSP
    vem do `SECURE_CSP` do Django 6, sem o pacote `django-csp`: uma
    dependência a menos, e o Admin já traz o nonce para a política nativa. A política
    é a mais estrita que o blog permite: sem `'unsafe-inline'` no
    estilo (nenhum template do blog tem estilo inline) e imagem só do próprio site
    (as capas vêm da mídia). O `Permissions-Policy` não tem configuração no Django e
    usa um middleware pequeno do próprio projeto.

## Testes

### RF-13 — A suíte cobre a configuração de produção

A suíte (`uv run pytest`, sem rede, sem tocar a pasta de dados real) cobre:

- a receita de build: o arquivo existe e traz o `--locked`, o `--no-dev`, o extra
  `prod`, o `collectstatic`, o `migrate` antes do gunicorn, a porta da variável
  `PORT` e as configurações de produção no start (RF-01, RF-02);
- `X-Forwarded-Proto: https` com as configurações de produção: sem redirect e cookies
  `Secure`; sem o cabeçalho: redirect 301 (RF-03);
- POST com `Origin` do próprio site aceito e com `Origin` de fora recusado com 403
  (RF-04);
- leitura de `ALLOWED_HOSTS` com espaços, vírgula no fim e valor vazio
  (RF-05);
- `ADMIN_URL` ausente, vazia, só barras, com e sem barra: o caminho lido e o Admin
  respondendo nele; o `robots.txt` sem o caminho e o login do Admin com
  `meta robots` (RF-14);
- a subida sem `SECRET_KEY`, ausente ou vazia, nas configurações de desenvolvimento
  e de produção (RF-15);
- leitura de `DIRETORIO_DADOS` ausente e presente: caminhos do banco, da mídia e do
  cache (RF-06);
- mídia com `DEBUG=False`: arquivo existente (200, `Content-Type`, `nosniff`),
  inexistente, pasta e caminho com `../` (404) (RF-07);
- a contagem no cache em arquivo vista por dois processos, e tentativas simultâneas
  que não passam do limite (RF-08);
- a trava de origem: sem segredo, desligada; com segredo, 403 sem o cabeçalho ou com
  valor errado, passagem com o atual e com o anterior (RF-09);
- o IP: `CF-Connecting-IP` só com a trava ligada, ignorado com ela desligada (RF-10);
- o log: erro 500 registrado, 404 sem registro, 403 da trava registrado sem o valor
  do cabeçalho (RF-11, RNF-05);
- `check --deploy` sem erro com as configurações de produção (RF-12);
- a CSP e o `Permissions-Policy` lidos na resposta das páginas públicas e do Admin,
  o HTML público sem script, estilo nem atributo de evento inline, e o `<style>`
  inline do Admin com o nonce do pedido (RF-16, RF-17, RNF-02).
