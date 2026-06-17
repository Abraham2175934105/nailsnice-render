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


# Script temporal de emergencia para encriptar contraseñas en producción
try:
	# Import here to avoid startup-time circular imports for manage commands
	import django
	django.setup()
	from django.contrib.auth.hashers import make_password
	from usuarios.models import Usuario

	usuarios_planos = Usuario.objects.filter(hash_contrasena__isnull=False).exclude(hash_contrasena__contains='$')
	if usuarios_planos.exists():
		print(f"--- [EMERGENCIA] Encontrados {usuarios_planos.count()} usuarios con clave plana. Encriptando... ---")
		for u in usuarios_planos:
			# If the stored value is '!' placeholder, set a secure default password before hashing
			raw = u.hash_contrasena if u.hash_contrasena and u.hash_contrasena != '!' else '12345678Ns.'
			u.hash_contrasena = make_password(raw)
			u.save(update_fields=['hash_contrasena'])
		print("--- [EMERGENCIA] ¡Todos los usuarios encriptados con éxito! ---")
except Exception as e:
	print(f"--- [EMERGENCIA ERROR]: {e} ---")
