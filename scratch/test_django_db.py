import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.db import connection
from usuarios.models import Usuario

print("--- DB ENGINE & HOST ---")
print(f"Engine: {connection.settings_dict['ENGINE']}")
print(f"Host: {connection.settings_dict.get('HOST')}")
print(f"Database: {connection.settings_dict.get('NAME')}")

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("Success: DB Connection successful.")
except Exception as e:
    print(f"Error: DB Connection failed: {e}")
    sys.exit(1)

print("\n--- Listing schemas/tables ---")
try:
    with connection.cursor() as cursor:
        if 'sqlite' in connection.settings_dict['ENGINE']:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        else:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables.")
        print("Tables:", sorted(tables))
except Exception as e:
    print(f"Error listing tables: {e}")

print("\n--- Checking Users ---")
try:
    users_count = Usuario.objects.count()
    print(f"Total users: {users_count}")
    for u in Usuario.objects.all()[:5]:
        print(f"User: ID={u.id_usuario}, Email={u.correo}, Name={u.nombre} {u.apellido}")
        try:
            print(f"  Rol asignado: {u.rol_asignado}")
        except Exception as e:
            print(f"  Error fetching rol_asignado: {e}")
except Exception as e:
    print(f"Error checking users: {e}")
