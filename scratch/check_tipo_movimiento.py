import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Profesional Beauty.settings')
django.setup()

from inventario.models import TipoMovimientoInventario

output_lines = []

output_lines.append("Checking records in database:")
for t in TipoMovimientoInventario.objects.all():
    output_lines.append(f"ID: {t.id_tipo_movimiento}, CODE: {t.codigo}, DESC: {t.descripcion}, DIR: {t.direccion}")

output_lines.append("\nChecking SQL file definitions:")
import re
try:
    with open('respaldo.sql', 'rb') as f:
        raw = f.read()
        enc = 'utf-16-le' if raw.startswith(b'\xff\xfe') else 'utf-8'
        content = raw.decode(enc, errors='replace')
    
    for line in content.splitlines():
        if 'tipo_movimiento_inventario' in line.lower():
            if 'insert' in line.lower() or 'create table' in line.lower():
                output_lines.append(line[:200])
except Exception as e:
    output_lines.append(f"Error reading respaldo.sql: {e}")

# Ensure scratch dir exists
os.makedirs('scratch', exist_ok=True)

# Write to file
with open('scratch/output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))
print("Output written successfully.")
