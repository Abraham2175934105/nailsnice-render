import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Profesional Beauty.settings')
django.setup()

from usuarios.models import Usuario

email = "testagent@example.com"
try:
    user = Usuario.objects.filter(correo=email).first()
    if user:
        user.delete()
        print("Success: Temporary test user deleted.")
    else:
        print("Success: Test user did not exist.")
except Exception as e:
    print(f"Error: Could not delete user: {e}")
