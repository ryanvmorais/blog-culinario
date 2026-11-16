# Política de segurança

## Versões suportadas

Só a versão mais recente (a branch `main`) recebe correções de segurança.

| Versão | Suportada |
|---|---|
| `main` | sim |
| commits anteriores, cópias e forks | não |

## Como reportar uma vulnerabilidade

Reporte **em privado**, pelos avisos de segurança do GitHub: abra a aba **Security and quality** do
repositório e escolha **Report a vulnerability**, ou use o
[link direto](https://github.com/ryanvmorais/blog-culinario/security/advisories/new). Não abra
issue nem pull request públicos para isso.

Inclua o necessário para reproduzir: o commit, os passos, o que você esperava e o que aconteceu, e
o impacto que você enxerga. Teste só numa cópia local do projeto.

O objetivo é **confirmar o recebimento em até 7 dias**.

## Política de divulgação

A divulgação é coordenada: a correção é preparada em privado, publicada, e só então o aviso é
divulgado. O prazo-alvo é de no máximo **90 dias** a partir do relato, ou antes se a correção
ficar pronta. O relator recebe o crédito no aviso, a menos que prefira não aparecer.

## Escopo

Este é um blog de receitas em Django feito como material educacional: páginas públicas de
receitas com busca e filtros, cadastro e login, comentários e o painel Admin. O que cabe aqui é
uma falha no código do projeto (views, formulários, autenticação, limite de tentativas, upload de
imagem, configurações de segurança), numa dependência ou num workflow do GitHub Actions.

O que as especificações em [specs/](specs/) registram como não-objetivo é decisão de escopo, não
vulnerabilidade. Dúvidas e sugestões comuns vão pelas
[issues](https://github.com/ryanvmorais/blog-culinario/issues).
