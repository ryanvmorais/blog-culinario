"""
Ponto de entrada WSGI do projeto Blog Culinário.

Expõe o callable WSGI na variável de módulo ``application``, que o gunicorn
serve em produção (ver ``railpack.json``). Sem ``DJANGO_SETTINGS_MODULE``, cai
nas configurações de produção (spec 011, ADR-2): um servidor WSGI só existe em
deploy, e esquecer a variável não pode subir o site com ``DEBUG=True``. O
``manage.py`` segue com as de desenvolvimento, e o ``runserver`` não lê este
padrão, porque importa este módulo depois de o ``manage.py`` definir a variável.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_culinario.settings.prod")

application = get_wsgi_application()
