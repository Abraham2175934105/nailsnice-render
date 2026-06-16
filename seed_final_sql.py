import os
import django
import random
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.db import connection

def seed():
    with connection.cursor() as cursor:
        print("Paso 1: Usuarios y Clientes...")
        cursor.execute("SELECT id_usuario FROM usuario")
        users = cursor.fetchall()
        if not users:
            # Crear admin si no existe nada
            cursor.execute("""
                INSERT INTO usuario 
                (correo, hash_contrasena, nombre, apellido, estado, es_staff, es_superusuario, creado_en, actualizado_en) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, ["admin@nails.com", "pbkdf2_sha256$600000$randomhash", "Admin", "Nails", "ACTIVO", 1, 1])
            cursor.execute("SELECT LAST_INSERT_ID()")
            users = [(cursor.fetchone()[0],)]
        
        for u in users:
            cursor.execute("INSERT IGNORE INTO clientes_cliente (usuario_id, puntos_fidelidad, creado_en, actualizado_en) VALUES (%s, %s, NOW(), NOW())", [u[0], 0])

        print("Paso 2: Catalogo...")
        cursor.execute("INSERT IGNORE INTO categoria_catalogo (nombre, activo, creado_en) VALUES (%s, %s, NOW())", ["General", 1])
        cursor.execute("SELECT id_categoria FROM categoria_catalogo LIMIT 1")
        cat_id = cursor.fetchone()[0]

        cursor.execute("INSERT IGNORE INTO subcategoria_catalogo (id_categoria, nombre, activo, creado_en) VALUES (%s, %s, %s, NOW())", [cat_id, "Insumos", 1])
        cursor.execute("SELECT id_subcategoria FROM subcategoria_catalogo LIMIT 1")
        sub_id = cursor.fetchone()[0]

        print("Paso 3: Productos y Variantes...")
        for i in range(10):
            name = f"Producto Seed {i}"
            slug = f"p-seed-{i}"
            cursor.execute("INSERT IGNORE INTO producto (id_subcategoria, nombre, slug, estado, creado_en) VALUES (%s, %s, %s, %s, NOW())", [sub_id, name, slug, "ACTIVO"])
            cursor.execute("SELECT id_producto FROM producto WHERE slug=%s", [slug])
            pid = cursor.fetchone()[0]
            cursor.execute("INSERT IGNORE INTO variante_producto (id_producto, sku, precio, activo, creado_en) VALUES (%s, %s, %s, %s, NOW())", [pid, f"SKU-{pid}", 50000.00, 1])

        print("Paso 4: Pedidos...")
        cursor.execute("SELECT id FROM clientes_cliente")
        clis = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT id_variante FROM variante_producto")
        vars = [r[0] for r in cursor.fetchall()]

        for i in range(15):
            cid = random.choice(clis)
            vid = random.choice(vars)
            num = f"ORD-{1000+i}"
            cursor.execute("""
                INSERT INTO pedido_venta 
                (id_usuario_cliente, numero_pedido, estado, subtotal, monto_envio, monto_impuesto, monto_descuento, monto_total, puntos_ganados, realizado_en, creado_en) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, [cid, num, 'PAGADO', 50000.00, 0, 0, 0, 50000.00, 10])
            cursor.execute("SELECT LAST_INSERT_ID()")
            pid = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO detalle_pedido_venta 
                (id_pedido, id_variante, cantidad, precio_unitario, total_linea, creado_en) 
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, [pid, vid, 1, 50000.00, 50000.00])

    print("Seed finalizado exitosamente.")

if __name__ == "__main__":
    seed()
