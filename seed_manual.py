import os
import django
import random
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

def seed():
    with connection.cursor() as cursor:
        print("Insertando Roles...")
        cursor.execute("INSERT IGNORE INTO rol_acceso (codigo, nombre, descripcion, es_sistema, creado_en) VALUES ('ADMIN', 'Administrador', 'Acceso total', 1, NOW()), ('CLIENTE', 'Cliente', 'Acceso básico', 1, NOW()), ('EMPLEADO', 'Empleado', 'Acceso ventas', 1, NOW())")
        
        print("Insertando Usuarios...")
        for i in range(10):
            cursor.execute(f"INSERT IGNORE INTO usuario (correo, hash_contrasena, nombre, apellido, estado, es_staff, es_superusuario, creado_en, actualizado_en) VALUES ('user{i}@example.com', 'pbkdf2_sha256$600000$p6Hk9o1x$b367675757', 'Nombre{i}', 'Apellido{i}', 'ACTIVO', 0, 0, NOW(), NOW())")
            
        print("Insertando Categorías...")
        cursor.execute("INSERT IGNORE INTO categoria_catalogo (nombre, slug, activo, creado_en) VALUES ('Esmaltes', 'esmaltes', 1, NOW()), ('Herramientas', 'herramientas', 1, NOW()), ('Cuidado', 'cuidado', 1, NOW()), ('Decoración', 'decoracion', 1, NOW()), ('Kits', 'kits', 1, NOW())")
        
        print("Insertando Marcas...")
        cursor.execute("INSERT IGNORE INTO marca_catalogo (nombre, activo, creado_en) VALUES ('NailsNice', 1, NOW()), ('Masglo', 1, NOW()), ('OPI', 1, NOW()), ('Essie', 1, NOW()), ('Harmony', 1, NOW())")

        print("Insertando Productos y Variantes...")
        # Obtener una subcategoría válida
        cursor.execute("SELECT id_subcategoria FROM subcategoria_catalogo LIMIT 1")
        row = cursor.fetchone()
        if row:
            sub_id = row[0]
            for i in range(10):
                slug = f"prod-seed-{i}"
                cursor.execute(f"INSERT IGNORE INTO producto (id_subcategoria, nombre, slug, estado, creado_en) VALUES ({sub_id}, 'Producto Prueba {i}', '{slug}', 'ACTIVO', NOW())")
                cursor.execute(f"SELECT id_producto FROM producto WHERE slug='{slug}'")
                p_id = cursor.fetchone()[0]
                cursor.execute(f"INSERT IGNORE INTO variante_producto (id_producto, sku, precio, activo, creado_en) VALUES ({p_id}, 'SKU-{p_id}', 25000.00, 1, NOW())")

        print("Insertando Bodegas...")
        cursor.execute("INSERT IGNORE INTO bodega (codigo, nombre, activo, creado_en) VALUES ('PRINCIPAL', 'Bodega Principal', 1, NOW()), ('NORTE', 'Bodega Norte', 1, NOW())")

    print("Seeding finalizado con éxito.")

if __name__ == '__main__':
    seed()
