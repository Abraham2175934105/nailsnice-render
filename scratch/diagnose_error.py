import os
import sys

# Ensure DATABASE_URL is set to sqlite locally so we don't connect to remote PostgreSQL
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'

import django
import traceback

# Append current workspace to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from inventario.views import editar_producto
from productos.models import VarianteProducto
from inventario.models import ProductoMaquillaje

def diagnose():
    print("=== Diagnosing /inventario/editar/2/ ===")
    
    # 1. Check database contents for ID 2 in both models
    print("\n1. Database query results:")
    try:
        vp = VarianteProducto.objects.filter(pk=2).first()
        print(f"VarianteProducto (id=2): {vp}")
        if vp:
            print(f"  - SKU: {vp.sku}")
            print(f"  - Nombre Variante: {vp.nombre_variante}")
            print(f"  - Producto ID: {vp.producto_id}")
            if vp.producto:
                print(f"    - Producto Nombre: {vp.producto.nombre}")
                print(f"    - Subcategoria: {vp.producto.subcategoria}")
                print(f"    - Marca: {vp.producto.marca}")
    except Exception as e:
        print(f"Error querying VarianteProducto: {e}")
        traceback.print_exc()

    try:
        pm = ProductoMaquillaje.objects.filter(pk=2).first()
        print(f"ProductoMaquillaje (id=2): {pm}")
        if pm:
            print(f"  - Nombre: {pm.nombre}")
            print(f"  - Stock: {pm.stock}")
            print(f"  - Precio: {pm.precio}")
    except Exception as e:
        print(f"Error querying ProductoMaquillaje: {e}")
        traceback.print_exc()

    # 2. Simulate GET request to editar_producto(request, 2)
    print("\n2. Simulating views.editar_producto(request, 2):")
    User = get_user_model()
    admin_user = User.objects.filter(correo='admin@profesionalbeauty.com').first() or User.objects.first()
    if not admin_user:
        print("No users found in database!")
        return

    factory = RequestFactory()
    request = factory.get('/inventario/editar/2/')
    request.user = admin_user
    
    try:
        response = editar_producto(request, 2)
        print(f"Response status code: {response.status_code}")
        if hasattr(response, 'rendered_content'):
            print("Rendered content preview:")
            print(response.rendered_content[:500])
    except Exception as e:
        print("\n!!! ERROR IN VIEW !!!")
        traceback.print_exc()

if __name__ == '__main__':
    diagnose()
