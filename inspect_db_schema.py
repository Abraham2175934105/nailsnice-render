import sqlite3
import os

path = 'db.sqlite3'
print('DB exists:', os.path.exists(path))
if not os.path.exists(path):
    raise SystemExit(1)

con = sqlite3.connect(path)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in cur.fetchall()]
print('tables:', tables)
print('\n=== schema for relevant tables ===')
relevant = {
    'marca_catalogo', 'categoria_catalogo', 'subcategoria_catalogo', 'producto',
    'variante_producto', 'imagen_producto', 'atributo_definicion', 'opcion_atributo',
    'regla_atributo_subcategoria', 'valor_atributo_producto', 'valor_atributo_variante',
    'usuario', 'rol_acceso', 'permiso_acceso', 'usuario_rol', 'rol_permiso',
    'perfil_empleado'
}
for name in tables:
    if name in relevant:
        print(f"\n-- {name}")
        for row in cur.execute(f"PRAGMA table_info('{name}')"):
            print(row)
        for row in cur.execute(f"PRAGMA foreign_key_list('{name}')"):
            if row:
                print('FK', row)
con.close()
