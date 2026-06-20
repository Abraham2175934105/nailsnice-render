import os
import sys

# Ensure DATABASE_URL is set to sqlite locally
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'

import django
# Append current workspace to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from inventario.views import editar_producto
from productos.models import VarianteProducto, SubcategoriaCatalogo, MarcaCatalogo
from inventario.models import Bodega

def test_get_and_post():
    User = get_user_model()
    admin_user = User.objects.filter(correo='admin@profesionalbeauty.com').first()
    
    factory = RequestFactory()
    
    print("\n--- Testing GET request ---")
    request_get = factory.get('/inventario/editar/2/')
    request_get.user = admin_user
    
    try:
        response_get = editar_producto(request_get, 2)
        print(f"GET Response status code: {response_get.status_code}")
    except Exception as e:
        print("GET Request failed with exception:")
        import traceback
        traceback.print_exc()

    print("\n--- Testing POST request (valid data) ---")
    subcat = SubcategoriaCatalogo.objects.first()
    brand = MarcaCatalogo.objects.first()
    bod = Bodega.objects.first()
    
    post_data = {
        'nombre_producto': 'Esmalte OPI Rojo Modificado',
        'descripcion': 'Nueva descripcion',
        'subcategoria': subcat.id_subcategoria,
        'marca': brand.id_marca if brand else '',
        'sku': 'SKU-OPI-RED-2',
        'nombre_variante': 'Rojo Brillante',
        'precio': '16000.00',
        'costo': '9000.00',
        'bodega': bod.id_bodega,
        'cantidad_existencia': '60',
        'cantidad_reservada': '0',
        'nivel_reorden': '5',
        'activo': 'on'
    }
    
    request_post = factory.post('/inventario/editar/2/', data=post_data)
    request_post.user = admin_user
    
    try:
        response_post = editar_producto(request_post, 2)
        print(f"POST Response status code: {response_post.status_code}")
        if response_post.status_code == 302:
            print("Redirect location:", response_post.url)
            # Check if database was updated
            v = VarianteProducto.objects.get(pk=2)
            print("Updated Variante name in DB:", v.nombre_variante)
            print("Updated parent Producto name in DB:", v.producto.nombre)
            print("Updated parent Producto category in DB:", v.producto.subcategoria)
            print("Updated parent Producto brand in DB:", v.producto.marca)
    except Exception as e:
        print("POST Request failed with exception:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_get_and_post()
