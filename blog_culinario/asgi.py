"""
Ponto de entrada ASGI do projeto Blog Culinário.

Expõe o callable ASGI na variável de módulo ``application``, utilizada por
servidores compatíveis com ASGI. Não usado no deploy atual (o gunicorn serve o
``wsgi.py``) — mantido pelo scaffold padrão do Django para o projeto poder
migrar para um servidor ASGI sem retrabalho. Como o ``wsgi.py``, cai nas
configurações de produção sem ``DJANGO_SETTINGS_MODULE`` (spec 011, ADR-2).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_culinario.settings.prod")

application = get_asgi_application()
