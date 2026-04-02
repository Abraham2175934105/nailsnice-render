import pymysql

try:
    # Establecer la conexión
    connection = pymysql.connect(
        host='127.0.0.1',
        port=3307,
        user='root',
        password='',
        database='nails_nice',
        cursorclass=pymysql.cursors.DictCursor # Opcional: para obtener resultados como diccionarios
    )
    print("✅ Conexión exitosa a MariaDB (Puerto 3307).")
    
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"📂 Se encontraron {len(tables)} tablas en 'nails_nice':")
        for table in tables:
            # Obtenemos el nombre de la tabla sin importar la clave del diccionario
            print(f"   - {list(table.values())[0]}")
            
    connection.close()
except Exception as e:
    print(f"Error al conectar: {e}")