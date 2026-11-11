---
feature: Correções da auditoria de interface
status: concluído
date: 2026-10-18
related:
  - 000-fundacao/requirements.md
  - 005-comentarios/requirements.md
origin: concepcao
---

# 008 — Correções da auditoria de interface — Tasks

## Etapa 1 — Tokens, botões e alinhamento

- [x] `static/css/tokens.css`: `--cor-borda-campo` e `--cor-erro-fundo`. — RF-08, RNF-02
- [x] `static/css/base.css`: campos usam `--cor-borda-campo`; `.mensagem--error` usa `--cor-erro-fundo`. — RF-08
- [x] `static/css/base.css`: `.botao` com `font: inherit`, peso 600, rótulo centrado e altura mínima; `.formulario .botao` de largura total no celular e do tamanho do rótulo acima de 720 px. — RF-10, ADR-1
- [x] `static/css/base.css`: `.estado-vazio`, `.pagina-formulario`, `.so-leitor-de-tela`. — RF-17, RF-03, ADR-5
- [x] `static/css/base.css`: capa com `aspect-ratio`; alvo da categoria com 24 px; bloco `prefers-reduced-motion`. — RF-09, RF-16, RF-11
- [x] `nucleo/test_interface.py`: testes de CSS e tokens (botão, capa, movimento reduzido, borda dos campos). — RF-08, RF-09, RF-10, RF-11, RF-16
- [x] Portão de qualidade. — 99 passed, ruff/black/mypy verdes

## Etapa 2 — Marcação e acessibilidade

- [x] `templates/includes/cartao_receita.html`: link da foto fora do foco e do leitor de tela. — RF-02
- [x] `receitas/templates/receitas/lista.html`: `h2` oculto antes da grade; frase do filtro ativo com "Limpar filtro"; estado vazio. — RF-03, RF-13, RF-17
- [x] `receitas/views.py`: nome da categoria e da tag no contexto do filtro. — RF-13
- [x] `receitas/templates/receitas/detalhe.html`: mensagens dentro de `#comentarios` (o aviso "Ainda não há comentários" segue o título, à esquerda). — RF-05, RF-17
- [x] `templates/base.html` e `templates/includes/mensagens.html`: bloco `mensagens` e `role="status"`. — RF-05
- [x] `usuarios/templates/usuarios/{login,cadastro}.html`: coluna centrada; ajuda com id e `<div>`. — RF-07, RF-17
- [x] `usuarios/forms.py`: `autocomplete` do e-mail. — RF-07
- [x] `templates/{404,403,500}.html`. — RF-04
- [x] `static/js/interacoes.js`: foco, Esc e clique fora no menu. — RF-06
- [x] `nucleo/test_interface.py`: testes de marcação e de JS. — RF-02 a RF-07, RF-13, RF-17
- [x] Portão de qualidade. — 99 passed, ruff/black/mypy verdes

## Etapa 3 — Home, ícone e fontes

- [x] `nucleo/templates/nucleo/home.html` e `templates/includes/rodape.html`: blog por fora, Django por dentro. — RF-01
- [x] `static/img/favicon.svg` e `<link rel="icon">` no `base.html`. — RF-12
- [x] `static/fonts/`, `static/css/fontes.css` e `base.html` sem Google Fonts. — RF-14, ADR-4
- [x] `nucleo/test_interface.py`: home, favicon e fontes. — RF-01, RF-12, RF-14
- [x] Portão de qualidade. — 99 passed, ruff/black/mypy verdes; 35 mutações pegas

## Etapa 4 — Tema escuro (commit separado)

- [x] `static/css/tokens.css`: bloco `prefers-color-scheme: dark`. — RF-15, ADR-3
- [x] `nucleo/test_interface.py`: contraste calculado dos pares do tema escuro. — RF-15
- [x] Portão de qualidade. — 128 passed, ruff/black/mypy verdes; 5 mutações do tema escuro pegas

## Etapa 5 — Catálogo, documentação e verificação no navegador

- [x] `docs/design-system.html`: token novo, botões, estado vazio, hero e tema escuro; contraste do escuro. — RNF-03
- [x] `README.md`, `CLAUDE.md`, `docs/stack.md` e `specs/README.md`: índice e regras novas. — RNF-03
- [x] Verificação em Chrome real: axe, Tab, CLS e `auditar_proporcoes.py` antes e depois. — RF-01 a RF-17
- [x] `assets/blog-culinario-django-home-receitas-desktop.webp`: capa da home refeita com as seis receitas reais e fotos (2560x2120, WebP q90, 474 KiB; substitui o `home-preview.png`). — RF-01
- [x] Portão de qualidade completo. — 128 passed, ruff/black/mypy verdes; `manage.py check` sem problemas

### Verificação em Chrome real (18/10/2026)

Banco e mídia descartáveis, fora do repositório; 22 combinações de página e tela
(390 e 1280 px), nos temas claro e escuro do sistema.

| Medida | Antes | Depois |
|---|---|---|
| Violações do axe-core 4.14.0 | link sem nome, salto de título, `aria-valid-attr-value` | 0 em 22 telas, nos dois temas |
| `auditar_proporcoes.py`: rótulo fora do centro | 12 ocorrências (8 botões), com 24 px de folga de um lado e de 239 a 355 do outro | 0 |
| `auditar_proporcoes.py`: botão fora da fonte do corpo | 20 ocorrências (8 botões, Arial 13,3 px contra Inter 16 px) | 0 |
| Botão "Entrar" no computador | 420 x 41 px, com 39 px de rótulo colado à esquerda | 160 x 48 px, rótulo no centro |
| Paradas de Tab nos cartões da lista | 27 | 18 |
| Mensagem do comentário | 1.274 px acima da tela, sem role | na tela (topo 59 px), `role="status"` |
| CLS da página da receita (foto atrasada em 0,8 s) | 0,226 (celular) e 0,186 (desktop) | 0 e 0 (0,005 no tema escuro) |
| `aria-describedby` quebrados no cadastro | 3 | 0 |
| Menu do celular por teclado | foco não entra, Esc e clique fora não fecham | foco no 1º link, Esc devolve o foco, clique fora fecha |
| Requisições ao Google Fonts | 2 | 0 |
| `/favicon.ico` | 404 | ícone SVG, 200 |

A `auditar_proporcoes.py` passou de 40 achados (12 + 20 FALHA e 8 SUGESTÃO) para 3, todos
SUGESTÃO e todos o mesmo caso, que é decisão registrada: o formulário de comentário fica à
esquerda, na coluna de leitura da receita (`bloco_solto_a_esquerda`).
