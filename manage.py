#!/usr/bin/env python
"""
Utilitário de linha de comando do Django para tarefas administrativas.

Ponto de entrada para todos os management commands do projeto:
    python manage.py runserver
    python manage.py migrate
    python manage.py createsuperuser
    (entre outros)
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Configura o módulo de settings padrão e executa o comando recebido."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_culinario.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
