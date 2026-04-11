"""
ASGI config for nailsnice project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')

django_asgi_app = get_asgi_application()

# In local HTTPS dev with uvicorn, serve static files similarly to runserver.
if settings.DEBUG:
	application = ASGIStaticFilesHandler(django_asgi_app)
else:
	application = django_asgi_app
