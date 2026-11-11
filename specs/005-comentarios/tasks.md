---
feature: Comentários em receitas
status: concluído
date: 2026-09-12
related:
  - 001-modelagem-receitas/requirements.md
  - 002-listagem-detalhe-receitas/requirements.md
  - 004-autenticacao/requirements.md
origin: concepcao
---

# 005 — Comentários em receitas — Tasks

## Etapa 1 — Modelo Comentario

- [x] `receitas/models.py`: model `Comentario` (`receita` `on_delete=CASCADE`, `autor` `on_delete=SET_NULL, null=True, blank=True`, `texto`, `aprovado` `default=True`, `criado_em`, `Meta.ordering = ["criado_em"]`, `__str__`). — RF-01
- [x] `uv run python manage.py makemigrations receitas` — gerou `0002_comentario.py`.
- [x] `uv run python manage.py migrate`.
- [x] Portão de qualidade parcial: verdes.

## Etapa 2 — Formulário e view de criação

- [x] `receitas/forms.py` (novo arquivo): `FormularioComentario` (`ModelForm`, campo `texto`, `clean_texto` rejeitando vazio/espaço). — RF-05
- [x] `receitas/views.py`: `ComentarioCreateView` (`LoginRequiredMixin`, `http_method_names = ["post"]`, `handle_no_permission()` customizado apontando `next` para `receitas:detalhe` — ADR-2, `post()` cria o comentário ou emite mensagem de erro — ADR-3). — RF-04, RF-06, RNF-02
- [x] `receitas/urls.py`: rota `"<slug:slug>/comentar/"` → `receitas:comentar`.
- [x] Portão de qualidade parcial: verdes (`manage.py check` também).

## Etapa 3 — Exibição na página de detalhe

- [x] `receitas/views.py`: `ReceitaDetailView.get_context_data()` acrescenta `comentarios` (`self.object.comentarios.filter(aprovado=True).select_related("autor")`) e `formulario_comentario`. — RF-02, RNF-01
- [x] `receitas/templates/receitas/detalhe.html`: seção `#comentarios` — lista com `{% empty %}`, autor removido tratado, formulário (autenticado) ou link de login com `?next=` (anônimo). — RF-02, RF-03
- [x] `static/css/base.css`: `.comentario`/`.comentario__meta` na seção 6.
- [x] Portão de qualidade parcial: verdes.

### Correção feita durante a implementação

Verificação visual mostrou que `<textarea>` não herdava a tipografia do
site (usava monospace padrão do navegador) — a regra
`.formulario__campo input` da spec 004 não cobria `textarea`. Estendida
para `.formulario__campo input, .formulario__campo textarea`.

## Etapa 4 — Moderação no admin

- [x] `receitas/admin.py`: `ComentarioAdmin` (`texto_curto` via `Truncator`, `list_display`, `list_editable = ["aprovado"]`, `list_filter`, `search_fields`, `autocomplete_fields`, `list_select_related`). — RF-07
- [x] Portão de qualidade parcial: verdes.

## Etapa 5 — Testes

- [x] `receitas/tests.py`: builder `_comentario(**kwargs)`; criação com campos esperados; excluir receita apaga comentários (cascade); excluir autor preserva comentário com `autor=None`. — RF-01
- [x] `receitas/tests.py`: comentário aprovado aparece na página (ordem cronológica); reprovado não aparece; autor removido mostra "Usuário removido". — RF-02
- [x] `receitas/tests.py`: HTML da página de detalhe contém o formulário para cliente autenticado e o link de login com `?next=` correto para anônimo. — RF-03
- [x] `receitas/tests.py`: POST autenticado válido cria o comentário e redireciona com mensagem de sucesso; POST com texto vazio/só espaço não cria nada e mostra mensagem de erro. — RF-04, RF-05
- [x] `receitas/tests.py`: POST anônimo na rota de comentário redireciona para `/usuarios/entrar/?next=/receitas/<slug>/`; logar em seguida volta pra essa URL. — RF-06
- [x] `receitas/tests.py`: listagem do admin responde 200; desmarcar `aprovado` remove o comentário da view pública (mesmo teste de RF-02, referenciado também como cobertura de RF-07). — RF-07
- [x] Portão de qualidade completo: `uv run ruff check . && uv run black --check . && uv run mypy . && uv run pytest` — **57 passed**; `manage.py check` sem issues.
- [x] Verificação visual manual (convite de login, formulário autenticado, comentário publicado, erro de comentário vazio) — screenshots conferidos.

### Correção feita durante a implementação

`_comentario()` criava um usuário com username fixo (`"comentarista"`)
quando nenhum autor era passado — o teste de ordenação cronológica (que
chama o builder duas vezes sem autor) quebrou com `IntegrityError` de
username duplicado. Corrigido gerando um username único por chamada
(`comentarista-<uuid curto>`).
