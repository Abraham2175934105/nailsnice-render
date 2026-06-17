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


try:
	from usuarios.models import Usuario
	# Usamos 'password' que es el nombre del atributo en el modelo de Django
	usuarios_planos = Usuario.objects.filter(password__isnull=False).exclude(password__contains='$')
    
	if usuarios_planos.exists():
		print(f"--- [EMERGENCIA] Encontrados {usuarios_planos.count()} usuarios con clave plana. Encriptando... ---")
		for u in usuarios_planos:
			# set_password hace el make_password y lo guarda en el campo correcto
			u.set_password('12345678Ns.')
			u.save()
		print("--- [EMERGENCIA] ¡Todos los usuarios encriptados con éxito! ---")
except Exception as e:
	print(f"--- [EMERGENCIA ERROR]: {e} ---")
