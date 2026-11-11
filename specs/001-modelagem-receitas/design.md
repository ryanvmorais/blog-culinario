---
feature: Modelagem de domínio das receitas (Categoria, Receita, Tag)
status: concluído
date: 2026-09-12
related: []
origin: concepcao
---

# 001 — Modelagem de domínio das receitas — design

## Visão geral da abordagem

Três models no app `receitas` (`Categoria`, `Tag`, `Receita`), um helper
compartilhado de geração de slug único (`receitas/utils.py`), e um
`ModelAdmin` por model em `receitas/admin.py`. Sem views/URLs públicas nesta
spec — só o domínio e a superfície de administração via `/admin/`.

## Layout de módulos

```
receitas/
  models.py     # Categoria, Tag, Receita
  utils.py      # gerar_slug_unico() — compartilhado pelos 3 models
  admin.py      # CategoriaAdmin, TagAdmin, ReceitaAdmin
  tests.py      # testes dos 3 models + admin (smoke)
  migrations/
    0001_initial.py
```

## Modelo de dados

### Categoria

| Campo | Tipo | Notas |
|---|---|---|
| `nome` | `CharField(max_length=80)` | **sem** `unique` — RF-01 permite duas categorias com o mesmo nome, distinguidas pelo slug (correção feita na implementação; a unicidade real é do `slug`) |
| `slug` | `SlugField(max_length=90, unique=True, blank=True)` | gerado em `save()` se vazio |

### Tag

| Campo | Tipo | Notas |
|---|---|---|
| `nome` | `CharField(max_length=40)` | **sem** `unique` — mesma razão de `Categoria` |
| `slug` | `SlugField(max_length=50, unique=True, blank=True)` | gerado em `save()` se vazio |

### Receita

| Campo | Tipo | Notas |
|---|---|---|
| `titulo` | `CharField(max_length=140)` | |
| `slug` | `SlugField(max_length=160, unique=True, blank=True)` | gerado em `save()` a partir de `titulo` |
| `resumo` | `CharField(max_length=280)` | usado em cartões de listagem (spec seguinte) |
| `ingredientes` | `TextField` | uma linha por ingrediente, formatação na spec de views |
| `modo_de_preparo` | `TextField` | idem |
| `tempo_preparo_minutos` | `PositiveIntegerField` | |
| `porcoes` | `PositiveSmallIntegerField` | |
| `imagem_capa` | `ImageField(upload_to="receitas/capas/%Y/%m/", blank=True)` | validators: extensão + tamanho (RF-04) |
| `categoria` | `ForeignKey(Categoria, on_delete=PROTECT, related_name="receitas")` | RF-03 |
| `tags` | `ManyToManyField(Tag, related_name="receitas", blank=True)` | RF-03 |
| `autor` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True, related_name="receitas")` | RF-03 |
| `publicado` | `BooleanField(default=False)` | RF-03 |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |
| `atualizado_em` | `DateTimeField(auto_now=True)` | |

`Meta.ordering = ["-criado_em"]` em `Receita`; `["nome"]` em `Categoria`/`Tag`.

## Componentes

### `gerar_slug_unico()` (receitas/utils.py)

Função pura: recebe a classe do model, o texto de origem e o nome do campo
slug; devolve um slug único (sufixo `-2`, `-3`, ... em caso de colisão).
Compartilhada pelos três models para não repetir a lógica de unicidade em
cada `save()`.

### `Categoria.save()` / `Tag.save()` / `Receita.save()`

Cada um chama `gerar_slug_unico(...)` só quando `self.slug` está vazio —
preserva um slug definido manualmente (ex.: editado no admin) em vez de
regenerar a cada save.

### Validação de imagem (RF-04)

Dois validators no campo `imagem_capa`:
- `FileExtensionValidator(["jpg", "jpeg", "png", "webp"])` — formato.
- `validar_tamanho_imagem` (função local em `models.py`) — rejeita acima de
  5 MB, lendo `arquivo.size`.

### `ReceitaAdmin`

`list_display`, `list_filter`, `search_fields` conforme RF-05;
`autocomplete_fields = ["categoria", "autor"]` + `list_select_related =
["categoria", "autor"]` para RNF-02. `prepopulated_fields = {"slug":
("titulo",)}` — mesma UX de preenchimento automático de `CategoriaAdmin`/
`TagAdmin`, por consistência (não estava em RF-05 explicitamente para
Receita, mas seria inconsistente deixar de fora).

## Interfaces

Nenhuma URL pública nesta spec. Superfície de interação é só o Django admin
(`/admin/receitas/categoria/`, `/admin/receitas/tag/`, `/admin/receitas/receita/`),
já registrado via `@admin.register`.

## ADRs

### ADR-1 — Slug gerado em `save()`, não via signal ou lib externa

**Decisão.** Cada model sobrescreve `save()` e chama `gerar_slug_unico()`
quando o slug está vazio.
**Alternativas.** (a) `pre_save` signal centralizando a lógica; (b) lib
`django-autoslug`.
**Porquê.** `save()` explícito é mais fácil de ler e testar (chamar
`objeto.save()` e inspecionar o resultado, sem precisar entender o
mecanismo de signals); e é mais didático mostrar como a lógica funciona por
dentro do que importar uma lib de 15 linhas equivalentes.
**Trade-off.** Repetição de uma linha de chamada em cada `save()` — aceitável
dado que a lógica em si mora só em `utils.py`.

### ADR-2 — Autor com `on_delete=SET_NULL`

**Decisão.** `Receita.autor` usa `SET_NULL` + `null=True, blank=True`.
**Alternativas.** (a) `CASCADE` (apaga as receitas junto com o usuário); (b)
`PROTECT` (impede apagar o usuário enquanto tiver receita).
**Porquê.** O conteúdo do blog (a receita) é o que tem valor de permanecer —
perder a atribuição de autoria é aceitável, perder o conteúdo não.
**Trade-off.** Receita "órfã" (sem autor) precisa de tratamento no template
da spec de views (ex.: exibir "Autor removido").

### ADR-3 — Validação de imagem via `validators=[...]` declarativos

**Decisão.** Extensão e tamanho validados por uma lista de `validators` no
campo, não por um `clean()` customizado no model.
**Alternativas.** `Receita.clean()` concentrando as duas checagens.
**Porquê.** Validators são reutilizáveis (se outro model ganhar campo de
imagem depois, importa a mesma função) e o Django já roda `full_clean()` nos
formulários do admin automaticamente — não precisa de código extra para
disparar a validação.
**Trade-off.** Nenhum relevante para o escopo atual.

## Impacto no código existente

Nenhum model existia antes; app `receitas` só tinha o esqueleto do
`startapp`. Sem migração de dado a considerar.

## Estratégia de testes

`pytest` + `pytest-django`, marcador `@pytest.mark.django_db`. Um builder
`_receita(**kwargs)` em `receitas/tests.py` cria uma receita mínima válida
com defaults sensatos, para os testes não repetirem os 8 campos obrigatórios
em cada caso. Grupos (réguas `# ---`): slug (RF-01/RF-02), relacionamentos e
defaults (RF-03), validação de imagem (RF-04), admin (RF-05 — smoke test com
`self.client` e um usuário `is_staff=True`).
