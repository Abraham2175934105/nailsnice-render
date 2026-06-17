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


# Script de emergencia asíncrono corregido
import threading
import django

def ejecutar_encriptacion():
	try:
		from usuarios.models import Usuario
		# Filtramos usando el atributo del modelo
		usuarios_planos = Usuario.objects.filter(password__isnull=False).exclude(password__contains='$')
        
		if usuarios_planos.exists():
			print(f"--- [EMERGENCIA] Encontrados {usuarios_planos.count()} usuarios con clave plana. Encriptando... ---")
			for u in usuarios_planos:
				u.set_password('12345678Ns.')
				u.save()
			print("--- [EMERGENCIA] ¡Todos los usuarios encriptados con éxito! ---")
		else:
			print("--- [EMERGENCIA] No se encontraron usuarios con clave plana. ---")
	except Exception as e:
		print(f"--- [EMERGENCIA ERROR EN HILO]: {e} ---")

# Lo ejecutamos en un hilo separado para evitar el bloqueo del contexto asíncrono de ASGI
threading.Thread(target=ejecutar_encriptacion, daemon=True).start()
