# 🤝 Contribuindo com o Blog Culinário

Obrigado pelo interesse! Este repositório não é só um blog de receitas — é um
laboratório de boas práticas em Django, e a sua colaboração ajuda a manter
isto como referência de qualidade para quem está aprendendo.

## 🚀 O que você pode aprimorar?

1. **Novas camadas de segurança:** hardening que faltou na spec original.
2. **Cobertura de testes:** cenários que ainda não têm teste.
3. **Clareza de comentários/docstrings:** trechos que confundiram você.
4. **Atividades para praticar:** novas ideias no README, com o aprendizado que
   cada uma ensina.

## 🛠️ Como enviar sua sugestão:

1. Faça o **Fork** do projeto.
2. Crie uma branch para sua modificação: `git checkout -b feature/melhoria-tecnica`.
3. Faça os commits seguindo [Conventional Commits](https://www.conventionalcommits.org/)
   (ex.: `feat:`, `fix:`, `docs:`, `chore:`...).
4. Envie suas alterações para o seu fork: `git push origin feature/melhoria-tecnica`.
5. Rode o portão de qualidade completo (ver
   [README → Qualidade e testes](README.md#qualidade-e-testes)) e garanta
   que está tudo verde.
6. Abra o **Pull Request** detalhando o quê e o porquê da mudança.

Mudança de funcionalidade (não de documentação/bug pontual)? Considere abrir
uma spec em `specs/` primeiro — veja `specs/README.md` para o formato.

## 📜 Diretrizes de qualidade:

- Siga o estilo já estabelecido no código (nomes em português, docstrings nas
  funções públicas, type hints completos).
- Nunca desative uma proteção de segurança (CSRF, validação de senha, etc.)
  sem justificar o porquê no PR.
- Mantenha a coerência com o restante do projeto — este é um material de
  estudo, e consistência importa mais que preferência pessoal.

Dúvidas? Abra uma [Issue](https://github.com/ryanvmorais/blog-culinario/issues).

---
Atenciosamente,
**Quem mantém o Blog Culinário**
