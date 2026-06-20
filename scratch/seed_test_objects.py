import os
import sys

# Ensure DATABASE_URL is set to sqlite locally
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'

import django
# Append current workspace to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.contrib.auth import get_user_model
from productos.models import CategoriaCatalogo, SubcategoriaCatalogo, MarcaCatalogo, Producto, VarianteProducto
from inventario.models import Bodega, SaldoInventario

def seed_objects():
    print("Seeding test database objects...")
    
    # 1. User
    User = get_user_model()
    admin, created = User.objects.get_or_create(
        correo='admin@profesionalbeauty.com',
        defaults={
            'nombre': 'Admin',
            'apellido': 'Beauty',
            'estado': 'ACTIVO',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print(f"Created admin user: {admin.correo}")
    else:
        print(f"Admin user already exists: {admin.correo}")
        
    # 2. Bodega
    bodega, created = Bodega.objects.get_or_create(
        codigo='PRINCIPAL',
        defaults={'nombre': 'Bodega Principal', 'activo': True}
    )
    print(f"Bodega: {bodega.nombre}")

    # 3. Categoria
    categoria, created = CategoriaCatalogo.objects.get_or_create(
        nombre='Manicure',
        defaults={'slug': 'manicure', 'activo': True}
    )
    print(f"Categoria: {categoria.nombre}")

    # 4. Subcategoria
    subcategoria, created = SubcategoriaCatalogo.objects.get_or_create(
        nombre='Esmaltes',
        categoria=categoria,
        defaults={'slug': 'esmaltes', 'activo': True}
    )
    print(f"Subcategoria: {subcategoria.nombre}")

    # 5. Marca
    marca, created = MarcaCatalogo.objects.get_or_create(
        nombre='OPI',
        defaults={'activo': True}
    )
    print(f"Marca: {marca.nombre}")

    # 6. Producto parent
    producto, created = Producto.objects.get_or_create(
        nombre='Esmalte OPI Rojo',
        defaults={
            'subcategoria': subcategoria,
            'marca': marca,
            'slug': 'esmalte-opi-rojo',
            'estado': 'ACTIVO',
            'creado_por': admin
        }
    )
    print(f"Producto: {producto.nombre}")

    # 7. VarianteProducto (force id_variante = 2)
    # Delete first if it exists to ensure clean state
    VarianteProducto.objects.filter(pk=2).delete()
    
    variante = VarianteProducto.objects.create(
        id_variante=2,
        producto=producto,
        sku='SKU-OPI-RED-2',
        nombre_variante='Rojo Intenso',
        precio=15000.00,
        costo=8000.00,
        activo=True
    )
    print(f"VarianteProducto created with ID 2: {variante}")

    # 8. SaldoInventario
    saldo, created = SaldoInventario.objects.get_or_create(
        variante=variante,
        bodega=bodega,
        defaults={
            'cantidad_existencia': 50,
            'cantidad_reservada': 0,
            'nivel_reorden': 5
        }
    )
    print(f"SaldoInventario: {saldo}")
    
    print("Database seeding completed.")

if __name__ == '__main__':
    seed_objects()
