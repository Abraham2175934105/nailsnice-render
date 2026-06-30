"""
ASGI config for Profesional Beauty project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')

# Aumentar drásticamente los hilos para vistas síncronas en Uvicorn.
# Esto previene el bloqueo del event loop (Timeout 500) en instancias con pocos cores.
os.environ.setdefault('ASGI_THREADS', '40')

django_asgi_app = get_asgi_application()

# In local HTTPS dev with uvicorn, serve static files similarly to runserver.
if settings.DEBUG:
	application = ASGIStaticFilesHandler(django_asgi_app)
else:
	application = django_asgi_app

