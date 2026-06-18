import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from usuarios.models import Usuario, RolAcceso, UsuarioRol

email = "testagent@example.com"
password = "AgentPassword123!"

try:
    # Check if user exists
    user = Usuario.objects.filter(correo=email).first()
    if user:
        user.delete()
        print("Existing test user deleted.")
        
    user = Usuario.objects.create_user(
        correo=email,
        password=password,
        nombre="Test",
        apellido="Agent",
        telefono="1234567890"
    )
    print("User created successfully.")
    
    # Assign Cliente role
    rol_cliente = RolAcceso.objects.filter(nombre=RolAcceso.CLIENTE).first()
    if rol_cliente:
        UsuarioRol.objects.update_or_create(
            usuario=user,
            defaults={'rol': rol_cliente}
        )
        print("Cliente role assigned successfully.")
    else:
        print("WARNING: Cliente role not found in database.")
except Exception as e:
    print(f"Error creating user: {e}")
