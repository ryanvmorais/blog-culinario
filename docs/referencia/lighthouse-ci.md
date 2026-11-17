# Lighthouse CI

Referência do workflow `.github/workflows/lighthouse.yml`, que audita as páginas
públicas do blog a cada mudança que pode afetar desempenho, acessibilidade ou SEO.

## O que audita

- **Páginas:** 5 públicas (home, lista e detalhe de receita, entrar e cadastro).
- **Perfis:** mobile e desktop, com 3 medições por página e a mediana.
- **Quando roda:** em PR que muda template, estático, view, model, o comando de
  dados ou a configuração; no push da `main`; e à mão (`workflow_dispatch`). O
  repositório é público, então não há teto de minutos.
- **Não é check obrigatório:** o Lighthouse varia em runner compartilhado.

## Como o servidor sobe

- Dados de `manage.py semear_dados_demo`: idempotente, recusa `DEBUG=False` e gera
  as capas com o Pillow, sem rede.
- `MODO_DEMONSTRACAO=True`, como na instância pública.
- `URL_PUBLICA` no host do próprio runner: a auditoria de canonical reprova outro
  domínio.

## Limites

Ficam em `.github/lighthouse/mobile.json` e `.github/lighthouse/desktop.json`.

| Nível | O que confere |
|---|---|
| **Erro** | acessibilidade, boas práticas e SEO abaixo de 95; CLS acima de 0,1; peso por página; as asserções `color-contrast`, `unsized-images`, `target-size` e `errors-in-console` |
| **Aviso** | a nota de Performance |

Os números servem de comparação relativa entre versões; os reais só existem em
produção.

## Manutenção

- **Página nova importante** entra nos dois JSON. O
  `receitas/test_semear_dados_demo.py` guarda que toda URL auditada responde 200 e
  que mobile e desktop auditam as mesmas páginas.
- **`@lhci/cli`** fica fixado em `LHCI_VERSION` no workflow. O Dependabot não vê um
  `npx`, então a versão sobe à mão; ao subir, recalibre os limites.
