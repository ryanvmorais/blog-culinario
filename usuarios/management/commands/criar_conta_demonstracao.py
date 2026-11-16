"""
Comando ``criar_conta_demonstracao``: a conta pública da instância de demonstração.

Com ``MODO_DEMONSTRACAO`` ligado, a tela de login mostra usuário e senha desta
conta, para o visitante ver o site logado sem se cadastrar (spec 009, RF-04). O
comando cria a conta ou, se ela já existe, devolve a senha e as permissões ao
estado esperado: ativa, sem staff e sem superusuário (RF-05). Rodar de novo
corrige uma senha trocada pelo Admin sem duplicar nada.

Roda também com o modo desligado (ADR-6), mas avisa: sem o modo, a conta publica
comentários de verdade.

Uso::

    uv run python manage.py criar_conta_demonstracao
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from blog_culinario.demonstracao import (
    SENHA_DEMONSTRACAO,
    USUARIO_DEMONSTRACAO,
    modo_demonstracao_ligado,
)


class Command(BaseCommand):
    """
    Cria ou restaura a conta de demonstração; ver a docstring do módulo.

    Uso::

        uv run python manage.py criar_conta_demonstracao
    """

    help = "Cria ou restaura a conta pública do modo demonstração."

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Cria a conta ou devolve senha e permissões ao estado esperado.

        Fluxo:
            1. Busca a conta ``visitante`` ou a cria.
            2. Grava a senha pública e desliga staff e superusuário.
            3. Informa se a conta foi criada ou atualizada.
            4. Avisa se o modo demonstração está desligado (ADR-6).

        Args:
            *args (Any): argumentos posicionais (não utilizados).
            **options (Any): argumentos nomeados do parser (não utilizados).
        """
        usuario, criada = User.objects.get_or_create(username=USUARIO_DEMONSTRACAO)
        usuario.set_password(SENHA_DEMONSTRACAO)
        usuario.is_active = True
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.save()

        estado = "criada" if criada else "atualizada"
        self.stdout.write(self.style.SUCCESS(f"Conta de demonstração {estado}."))

        if not modo_demonstracao_ligado():
            self.stdout.write(
                self.style.WARNING(
                    "MODO_DEMONSTRACAO está desligado: com esta conta, os "
                    "comentários são publicados de verdade."
                )
            )
