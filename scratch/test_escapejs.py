import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.template.defaultfilters import escapejs
from django.utils.html import escape

json_str = '[{"nombre": "Servicio de Uñas", "variante": "Uñas Acrílicas"}]'
escaped_js = escapejs(json_str)
escaped_html = escape(json_str)

print("--- RAW JSON ---")
print(json_str)
print("\n--- ESCAPEJS ---")
print(escaped_js)
print("\n--- HTML ESCAPE ---")
print(escaped_html)
