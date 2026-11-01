![Blog Culinário: página inicial com receitas simples para todos os dias](assets/blog-culinario-django-home-receitas-desktop.webp)

# 🍲 Blog Culinário | Blog Multipáginas Educacional em Django

**Português (Brasil)** · [English](README.en.md)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-database-003B57?logo=sqlite&logoColor=white)
![deps](https://img.shields.io/badge/deps-uv-DE5FE9)
[![CI](https://github.com/ryanvmorais/blog-culinario/actions/workflows/ci.yml/badge.svg)](https://github.com/ryanvmorais/blog-culinario/actions/workflows/ci.yml)
![Lint](https://img.shields.io/badge/lint-ruff-261230)
![Format](https://img.shields.io/badge/style-black-000000)
![Types](https://img.shields.io/badge/types-mypy-2A6DB2)
![License](https://img.shields.io/badge/license-MIT-green)

Este repositório contém um **Blog Culinário multipáginas em Django**, criado como material educacional. Não é (só) um site de receitas: é uma referência para quem está aprendendo a construir uma aplicação web completa em Python, com **modelagem de domínio**, **autenticação nativa** e **segurança aplicada**, indo além do CRUD básico de tutorial.

### 🎯 Objetivo do Projeto:

Demonstrar como as peças de uma aplicação Django real se encaixam (modelagem, views, templates com herança, formulários, admin customizado, upload de imagem e segurança) em código que você pode ler de cima a baixo e entender o porquê de cada decisão, não só o "como".

---

### 📚 O que você vai aprender com este projeto?

Este projeto foi estruturado para consolidar pilares fundamentais de engenharia de software:

- **Modelagem de Domínio:** relacionamentos reais entre `Receita`, `Categoria`, `Tag` e `Comentario`, com políticas explícitas de `on_delete` para cada um.
- **Dois Estilos de View:** baseadas em função (`nucleo`) e em classe (`receitas`), lado a lado, para comparar as duas abordagens.
- **Design System Próprio:** herança de templates (`base.html` + blocks) e CSS puro em `static/css/tokens.css`, sem framework de frontend nem build step. Fontes hospedadas no projeto, tema claro e escuro do sistema só por variáveis de cor, e um catálogo visual em `docs/design-system.html`.
- **Autenticação Nativa:** `django.contrib.auth` sem lib externa, com limite de tentativas de login por IP.
- **Segurança Aplicada:** honeypot e time-trap no formulário de comentário, validação de upload de imagem, segredos fora do código.
- **Interface Auditada:** acessibilidade conferida em navegador real (axe-core, teclado, contraste, tema escuro) e guardada por testes, a partir da spec 008.
- **Qualidade Automatizada:** suíte de testes com `pytest` e um pipeline de CI que roda o mesmo portão de qualidade usado localmente.

---

### 🧠 Guia de Implementação (A Lógica por trás do Código):

Para quem está começando, o maior desafio não é decorar comandos do Django, mas entender a **montagem do raciocínio** de uma aplicação real. Confira os pilares da construção deste projeto:

1. **Apps por Domínio, não por Camada:** `nucleo` (institucional), `receitas` (o domínio principal) e `usuarios` (autenticação). Cada app cabe numa frase, o que facilita entender onde mexer.
2. **Configuração por Ambiente:** `settings/` é um pacote, não um arquivo só. `base.py` tem o que nunca muda; `dev.py` e `prod.py` só sobrescrevem o que é específico do ambiente. É o padrão que evita o clássico "esqueci de trocar DEBUG antes do deploy".
3. **Banco de Dados de Propósito:** SQLite não por preguiça, mas por decisão: zero configuração para quem clona o repo, já que o objetivo é aprender Django, não administrar um banco.
4. **Identidade Visual do Zero:** um design system pequeno em `static/css/tokens.css` (cores, tipografia, espaçamento como variáveis CSS) mantém o projeto 100% focado em Python, sem esconder como um front-end é montado.
5. **Segurança em Camadas:** limite de tentativas por IP (login e comentário) e honeypot + time-trap no formulário de comentário, implementados a partir de achados de uma auditoria de segurança real, não de especulação.
6. **Desenvolvimento Guiado por Spec:** cada funcionalidade nova nasce em `specs/` antes do código, com requisitos, design e tarefas, e aprovação antes de avançar de fase.

---

### 🛠️ Tecnologias e Ferramentas:

Para garantir a melhor experiência de aprendizado, o projeto utiliza as seguintes tecnologias:

| Ferramenta | Descrição |
| :--- | :--- |
| **Python 3.12+** | Linguagem base do projeto. |
| **Django 6.1** | Framework web "com baterias incluídas", para toda a lógica, o ORM e o admin. |
| **SQLite** | Banco de dados relacional: um arquivo, zero configuração. |
| **uv** | Gerenciador de dependências e ambientes virtuais, com lockfile reprodutível. |
| **Pillow** | Processa e valida as imagens de capa das receitas. |
| **django-environ** | Lê `SECRET_KEY` e `DEBUG` do ambiente em vez de deixá-los no código. |
| **WhiteNoise** | Serve os arquivos estáticos em produção sem precisar de Nginx ou CDN. |

As ferramentas de qualidade (Ruff, Black, Mypy e Pytest) estão em [Qualidade e testes](#qualidade-e-testes). Para o porquê de cada escolha (e as alternativas descartadas), veja [docs/stack.md](docs/stack.md).

---

### ⚙️ Como rodar o projeto localmente:

**Pré-requisitos:** [Python 3.12+](https://www.python.org/downloads/) e [uv](https://docs.astral.sh/uv/getting-started/installation/), que cria e gerencia o ambiente virtual automaticamente. Para conferir, rode `python --version` e `uv --version`.

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/ryanvmorais/blog-culinario.git
    cd blog-culinario
    ```
2.  **Instale as dependências:**
    ```bash
    uv sync
    ```
3.  **Crie as tabelas do banco:**
    ```bash
    uv run python manage.py migrate
    ```
4.  **Suba o servidor:**
    ```bash
    uv run python manage.py runserver
    ```

Acesse `http://127.0.0.1:8000/`. Não é preciso configurar nenhuma variável de ambiente para rodar localmente; veja o `.env.example` se quiser customizar algo.

Quer ver o site com receitas de exemplo sem cadastrar nada? Rode `uv run python manage.py semear_dados_demo`: ele cria receitas, capas e comentários fictícios (só em desenvolvimento, e sem duplicar se rodar de novo).

> ⚠️ **Nota sobre o Admin:** quer um usuário para acessar `/admin/`? Rode `uv run python manage.py createsuperuser` e siga as instruções no terminal.

---

### Qualidade e testes

O projeto roda uma suíte de testes automatizados (`pytest`) e um portão de qualidade antes de qualquer commit:

```bash
# Lint + ordem de imports
uv run ruff check .

# Formatação
uv run black --check .

# Checagem de tipos
uv run mypy .

# Testes
uv run pytest
```

O mesmo portão roda automaticamente em CI (`.github/workflows/ci.yml`) a cada PR e a cada push na `main`, no Python 3.12 (o piso do projeto) e no 3.14. Toda segunda-feira, o `.github/workflows/pip-audit.yml` audita o `uv.lock` em busca de CVEs. Já o `.github/workflows/lighthouse.yml` audita as páginas públicas (acessibilidade, SEO, contraste, alvos de toque, CLS e peso) em mobile e desktop a cada PR que muda a interface e a cada push na `main`; ele não bloqueia o merge, porque o Lighthouse oscila em servidor compartilhado. Para o mapa de cada tecnologia da stack (o que é, por que foi escolhida, o que estudar), veja [docs/stack.md](docs/stack.md). Para as especificações de cada funcionalidade, veja [specs/](specs/). Para o detalhamento de arquitetura e convenções, veja [CLAUDE.md](CLAUDE.md).

---

### 📋 Atividades para praticar (Desafios de Evolução):

Para exercitar o que você aprendeu e dominar o Django, tente implementar estas novas funcionalidades:

1. **🔍 Filtro por Tempo de Preparo:** adicione um campo `tempo_de_preparo` filtrável na listagem de receitas.
   - **O Aprendizado:** `QuerySet.filter()` combinado com um formulário de busca.
2. **🎲 Receita Aleatória:** crie uma rota que leve a uma receita publicada escolhida ao acaso.
   - **O Aprendizado:** `order_by("?")` do Django e os limites de performance dessa abordagem num banco maior.
3. **💬 Paginação de Comentários:** pagine os comentários de uma receita com muitos comentários.
   - **O Aprendizado:** o `Paginator` aplicado a um queryset relacionado (não à página inteira), e como ajustar o template para paginar só uma seção.
4. **🐘 Troca de Banco de Dados:** troque o SQLite por PostgreSQL num ambiente separado.
   - **O Aprendizado:** como `DATABASES` isola o projeto do banco físico: o resto do código não muda uma linha.

---

### 🧭 Continue praticando:

Este projeto faz parte de uma trilha de estudos em Python. Depois deste, experimente:

- **[webvigil](https://github.com/ryanvmorais/webvigil):** um scanner de vulnerabilidades web (DAST) em Python, para ver a segurança do outro lado.
- **[Portfólio Dinâmico com Django](https://github.com/ryanvmorais/portfolio-dinamico):** outro projeto Django, com foco em segurança avançada (honeypot, rate limit, CSP) e otimização de consultas.

Veja todos os projetos e vídeos do canal em [aprenda-com-ryan-morais](https://github.com/ryanvmorais/aprenda-com-ryan-morais).

---

### 💡 Ficou com alguma dúvida ou tem sugestões?

Encontrou algo que poderia estar mais didático, teve dificuldade com alguma configuração, ou pensou numa melhoria que tornaria este projeto ainda mais útil como referência? Estou aqui para ajudar!

- **Abra uma [Issue](https://github.com/ryanvmorais/blog-culinario/issues):** descreva sua dúvida ou sugestão. É a melhor forma de construirmos um material de referência sólido para a comunidade e ajudarmos outros desenvolvedores que possam ter a mesma dúvida.
- **Contribua com código:** quer propor uma melhoria? Veja o passo a passo no [CONTRIBUTING.md](CONTRIBUTING.md).
- **Me mande um e-mail:** se preferir algo mais privado, escreva para [**contato@ryanmorais.com.br**](mailto:contato@ryanmorais.com.br).

Ficarei muito feliz em acompanhar sua evolução com o framework Django e receber seu feedback para melhorar cada vez mais a qualidade deste material de estudo! 🤝

---

### ⚖️ Licença

Este projeto está sob a **Licença MIT**. Isso significa que você pode usar, copiar e modificar o código à vontade, inclusive nos seus projetos. Para mais detalhes, consulte o arquivo [LICENSE](LICENSE).
