import os
import sys
# Agregar el directorio actual al path para evitar ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.getcwd())

import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'
# Asegurar que DEBUG sea True para ver la traza completa
os.environ['DJANGO_DEBUG'] = 'True'
django.setup()

from inventario.views import editar_producto
from productos.models import VarianteProducto

def test_view():
    print("Iniciando prueba de vista editar_producto...")
    try:
        # Intentar obtener la variante con ID 2
        v = VarianteProducto.objects.filter(pk=2).first()
        print(f"Variante ID 2 encontrada: {v}")
        if v:
            print(f"Producto asociado: {v.producto}")
            if v.producto:
                print(f"Subcategoría: {v.producto.subcategoria}")
                print(f"Marca: {v.producto.marca}")
    except Exception as db_err:
        print(f"No se pudo consultar VarianteProducto directamente: {db_err}")
        
        # Crear un request simulado
        factory = RequestFactory()
        request = factory.get('/inventario/editar/2/')
        
        # Crear un usuario administrador simulado para pasar la validación
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            # Buscar cualquier usuario o crear uno
            admin_user = User.objects.first()
        
        request.user = admin_user
        print(f"Simulando request con usuario: {request.user}")
        
        # Llamar a la vista directamente
        response = editar_producto(request, 2)
        print("Status code de la respuesta:", response.status_code)
        if hasattr(response, 'render'):
            response.render()
            print("Renderizado completado con éxito.")
    except Exception as e:
        import traceback
        print("\n!!! EXCEPCIÓN DETECTADA !!!")
        traceback.print_exc()

if __name__ == "__main__":
    test_view()
