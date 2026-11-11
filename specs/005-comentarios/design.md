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

# 005 — Comentários em receitas — design

## Visão geral da abordagem

Um model novo (`Comentario`) dentro do app `receitas` (ADR-1), um form,
uma view de criação `@login_required`, e mudanças em
`ReceitaDetailView`/`detalhe.html` para exibir a lista + o formulário (ou
o convite de login). Admin ganha `ComentarioAdmin` com moderação por flag.

## Layout de módulos

```
receitas/
  models.py    # + Comentario
  forms.py     # novo: FormularioComentario
  views.py     # + ComentarioCreateView; ReceitaDetailView ganha comentarios/formulario no contexto
  urls.py      # + "<slug>/comentar/"
  admin.py     # + ComentarioAdmin
  migrations/
    0002_comentario.py
  templates/receitas/
    detalhe.html  # + seção de comentários
```

## Modelo de dados

### Comentario

| Campo | Tipo | Notas |
|---|---|---|
| `receita` | `ForeignKey(Receita, on_delete=CASCADE, related_name="comentarios")` | RF-01 |
| `autor` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True, related_name="comentarios")` | mesma política de `Receita.autor` (spec 001, ADR-2) |
| `texto` | `TextField` | validação de não-vazio no form, não no model (ADR-3) |
| `aprovado` | `BooleanField(default=True)` | ADR-4 |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |

`Meta.ordering = ["criado_em"]` — mais antigo primeiro (conversa
cronológica, RF-02).

## Componentes

### `FormularioComentario` (`receitas/forms.py`, RF-05)

```python
class FormularioComentario(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 4})}

    def clean_texto(self):
        texto = self.cleaned_data["texto"].strip()
        if not texto:
            raise forms.ValidationError("O comentário não pode ficar vazio.")
        return texto
```

`TextField` sem `blank=False` já rejeita string vazia, mas **não** rejeita
uma string só de espaços (é "verdadeira" para o Django) — daí o
`clean_texto` fazer o `.strip()` explícito.

### `ComentarioCreateView` (`receitas/views.py`, RF-04, RF-06, RNF-02)

```python
class ComentarioCreateView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def handle_no_permission(self):
        url_receita = reverse("receitas:detalhe", kwargs={"slug": self.kwargs["slug"]})
        return redirect_to_login(url_receita, self.get_login_url(), self.get_redirect_field_name())

    def post(self, request, slug):
        receita = get_object_or_404(Receita, slug=slug, publicado=True)
        form = FormularioComentario(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.receita = receita
            comentario.autor = request.user
            comentario.save()
            messages.success(request, "Comentário publicado!")
        else:
            messages.error(request, "O comentário não pode ficar vazio.")
        return redirect(reverse("receitas:detalhe", kwargs={"slug": slug}) + "#comentarios")
```

`handle_no_permission` sobrescrito de propósito — ver ADR-2.

### `ReceitaDetailView.get_context_data()` (novo método, RF-02, RF-03, RNF-01)

```python
def get_context_data(self, **kwargs):
    contexto = super().get_context_data(**kwargs)
    contexto["comentarios"] = self.object.comentarios.filter(aprovado=True).select_related("autor")
    contexto["formulario_comentario"] = FormularioComentario()
    return contexto
```

### `ComentarioAdmin` (`receitas/admin.py`, RF-07)

```python
@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ["texto_curto", "receita", "autor", "aprovado", "criado_em"]
    list_editable = ["aprovado"]
    list_filter = ["aprovado"]
    search_fields = ["texto"]
    autocomplete_fields = ["receita", "autor"]
    list_select_related = ["receita", "autor"]

    @admin.display(description="Comentário")
    def texto_curto(self, obj):
        return Truncator(obj.texto).chars(60)
```

`list_editable` permite marcar/desmarcar `aprovado` direto na listagem,
sem abrir cada comentário — a forma mais rápida de moderar em volume.

### Template (`detalhe.html`)

Nova seção `#comentarios`: lista os `comentarios` do contexto (com
`{% empty %}` para "ainda não há comentários"), e — condicional a
`user.is_authenticated` — o formulário (`POST` para
`receitas:comentar`) ou um link de login com `?next=` para a própria
receita.

## Interfaces

| Método | URL | View | Nome |
|---|---|---|---|
| POST | `/receitas/<slug>/comentar/` | `ComentarioCreateView` | `receitas:comentar` |

Nenhuma URL de listagem/edição de comentário — tudo acontece na página de
detalhe da receita (formulário) ou no admin (moderação).

## ADRs

### ADR-1 — Comentario vive no app `receitas`, não num app próprio

**Decisão.** O model `Comentario` é adicionado a `receitas/models.py`.
**Alternativas.** Um quarto app (`comentarios`).
**Porquê.** Comentário não existe sem uma receita — é uma extensão direta
do domínio já modelado ali, sem estado ou tela própria fora do contexto de
uma receita. Um app próprio para um model dependente e sem rota de listagem
independente adicionaria fragmentação sem benefício (README já descreve
"apps por domínio, não por camada").
**Trade-off.** `receitas/models.py` cresce um pouco mais; aceitável no
tamanho atual do projeto.

### ADR-2 — `next` aponta para a página da receita, não para o endpoint de POST

**Decisão.** `ComentarioCreateView` sobrescreve `handle_no_permission()`
para redirecionar ao login com `next` = URL de `receitas:detalhe`, não a
URL da própria view (comportamento padrão do `LoginRequiredMixin`).
**Alternativas.** Deixar o `next` default do `LoginRequiredMixin`, que
usa `request.get_full_path()` (a URL do próprio endpoint de comentário).
**Porquê.** O endpoint de comentário só aceita `POST`
(`http_method_names = ["post"]`). Se o `next` apontasse pra ele, o
redirect pós-login (um `GET` do navegador) bateria num 405 — quebrando
justamente o fluxo que a spec 004 (RF-05) preparou. Apontar pra página da
receita é também mais correto para o usuário: é para lá que ele queria ir.
**Trade-off.** Uma pequena sobrescrita de método a mais; sem isso o
fluxo simplesmente não funciona.

### ADR-3 — Erro de validação via mensagem, não formulário reexibido inline

**Decisão.** Comentário inválido (vazio) redireciona de volta à receita
com `messages.error(...)`, não re-renderiza a página de detalhe com o
formulário e os erros inline.
**Alternativas.** `ComentarioCreateView` como `FormView`/`CreateView`
completo, capaz de re-renderizar `detalhe.html` com o form inválido.
**Porquê.** Re-renderizar `detalhe.html` exigiria duplicar todo o
contexto que `ReceitaDetailView` monta (receita, tags, outros
comentários...) dentro de uma view diferente — ou uma composição mais
elaborada entre as duas views. Uma mensagem de erro + redirect é
consistente com o padrão já estabelecido em login/logout/cadastro (spec
004, ADR-3) e resolve o único caso de erro possível aqui (texto vazio) sem
essa duplicação.
**Trade-off.** O texto digitado se perde se o comentário for rejeitado —
aceitável porque o único motivo de rejeição é "ficou vazio", ou seja, não
há conteúdo de valor para preservar.

### ADR-4 — Comentário nasce aprovado (moderação reativa, não fila prévia)

**Decisão.** `Comentario.aprovado` tem `default=True` — o comentário
aparece imediatamente; o admin modera removendo a aprovação depois, se
necessário.
**Alternativas.** `default=False` + fila de aprovação obrigatória antes de
qualquer comentário aparecer.
**Porquê.** Todo comentarista já passou pela autenticação (spec 004) —
o principal vetor de spam anônimo já está fechado. Para um blog de baixo
volume, exigir aprovação prévia de **todo** comentário criaria atrito sem
benefício proporcional; a extensão de segurança mais completa (rate
limiting, revisão de conteúdo) já está prevista na auditoria de segurança
do roadmap, não nesta spec.
**Trade-off.** Um comentário inadequado fica visível até o admin agir —
aceitável dado o volume esperado e o público (usuários autenticados).

## Impacto no código existente

- `receitas/models.py`: + `Comentario`.
- `receitas/forms.py`: novo arquivo, `FormularioComentario`.
- `receitas/views.py`: + `ComentarioCreateView`; `ReceitaDetailView` ganha
  `get_context_data()`.
- `receitas/urls.py`: + rota `comentar/`.
- `receitas/admin.py`: + `ComentarioAdmin`.
- `receitas/templates/receitas/detalhe.html`: + seção de comentários.
- Nenhuma mudança em `usuarios` — reaproveita `LOGIN_URL` e o fluxo de
  login/mensagens como estão.

## Estratégia de testes

Builders novos em `receitas/tests.py`: `_comentario(**kwargs)` (reaproveita
`_receita`). Grupos: modelo (RF-01: criação, cascade ao excluir receita,
`SET_NULL` ao excluir autor), exibição (RF-02: só aprovados, ordem,
"Usuário removido"), formulário condicional (RF-03: presença do form vs.
link de login com `?next=` correto no HTML), criação (RF-04/RF-05: POST
válido cria e redireciona com mensagem; POST vazio/espaço não cria nada),
login obrigatório (RF-06: POST anônimo redireciona para
`/usuarios/entrar/?next=/receitas/<slug>/` — a página, não o endpoint —
e login em seguida volta pra lá), admin (RF-07: listagem com os filtros;
desmarcar `aprovado` via `ComentarioAdmin` e conferir que a view pública
deixa de mostrar o comentário).
