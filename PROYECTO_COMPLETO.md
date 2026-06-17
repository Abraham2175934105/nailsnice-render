# PROYECTO_COMPLETO

## Manual de Instalación y Configuración — Nails Nice

Última actualización: 2026-06-17

Resumen: este documento describe paso a paso la instalación local, la preparación e importación de la base de datos (Neon/Postgres) mediante PGAdmin 4 o psql, el despliegue en Render y los requisitos del sistema (WeasyPrint, dependencias nativas), seeds idempotentes y acciones post-despliegue.

---

**Contenido**

- 1. Requisitos previos
- 2. Estructura del proyecto
- 3. Instalación local (entorno de pruebas)
   - 3.1 Crear entorno virtual e instalar dependencias
   - 3.2 Archivo `.env` y variables obligatorias
   - 3.3 Migraciones y superusuario
- 4. Base de datos (Neon) — importación con PGAdmin / psql
   - 4.1 Preparar la base en Neon
   - 4.2 Importar `respaldo.sql` y ejecutar `seed_initial_data.sql` (PGAdmin Query Tool)
   - 4.3 Ajustar secuencias (`setval`) y verificación
- 5. Despliegue en Render
   - 5.1 Archivos importantes (`Procfile`, `render.yaml`, `requirements.txt`)
   - 5.2 Variables de entorno en Render
   - 5.3 Build & Start commands
- 6. Dependencias del sistema y WeasyPrint (reportes PDF)
   - 6.1 Recomendación: usar Docker para Render o instalar paquetes OS
- 7. Seeds: buenas prácticas y pasos seguros para Neon
- 8. Backups y restauración (pg_dump / pg_restore)
- 9. Solución de errores comunes
- 10. Checklist post-despliegue

---

## 1. Requisitos previos

- Sistema: Debian/Ubuntu recomendado para servidores; Windows/macOS para desarrollo local.
- Python 3.10+ (el repo usa Python 3.14 en contexto de despliegue; valide con `python --version`).
- PostgreSQL compatible (Neon). Para importación usar PGAdmin 4 o `psql`.
- Node/npm no obligatorios salvo que uses frontends específicos; `pip` para dependencias Python.

Herramientas de administración:

- `git` (gestión del repo)
- `psql` (cliente Postgres) o PGAdmin 4 para import/queries
- `docker` (opcional, recomendado para producción/Render con dependencias nativas)

## 2. Estructura del proyecto (resumen)

- Código Django principal: `python/Nails_Nice_py/` (contiene `manage.py`, `requirements.txt`, `nailsnice/` app)
- Archivo de seeds: `python/Nails_Nice_py/seed_initial_data.sql`
- Archivo de respaldo de esquema: `respaldo.sql` (usar como referencia)
- Archivos de despliegue: `Procfile`, `render.yaml`, `.env.example`

## 3. Instalación local (entorno de pruebas)

3.1 Crear entorno virtual e instalar dependencias

1. Abrir terminal en `python/Nails_Nice_py/`.
2. Crear y activar virtualenv:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3.2 Archivo `.env` y variables obligatorias

Cree un archivo `.env` (nunca lo suba al repo). Aquí un ejemplo mínimo (`.env.example` ya está incluido):

```env
# Django
DJANGO_SECRET_KEY=tu_secreto_largo_y_seguro
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database (usar URL proporcionada por Neon en formato postgres://)
DATABASE_URL=postgres://usuario:pass@host:port/dbname

# Email / Otros (opcional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

3.3 Migraciones y superusuario

```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario (interactivo)
python manage.py createsuperuser

# Iniciar servidor local
python manage.py runserver
```

## 4. Base de datos (Neon) — Importación con PGAdmin o psql

4.1 Preparar la base en Neon

1. Crear base de datos y obtener la cadena de conexión (Neon Dashboard → Connection). Copie `postgres://...`.
2. En PGAdmin 4: crear un nuevo Server con esa conexión.

4.2 Importar `respaldo.sql` y ejecutar `seed_initial_data.sql`

Opción A — PGAdmin (UI)

1. Conéctese al Server Neon en PGAdmin.
2. Use `Query Tool` para ejecutar `respaldo.sql` primero (si necesita crear el esquema). Si tiene un archivo grande, use la opción `Restore` o `Backup/Restore` según el formato.
3. Ejecutar `seed_initial_data.sql` en `Query Tool` conectándose a la base destino. Nuestro `seed_initial_data.sql` ya contiene cláusulas `ON CONFLICT DO NOTHING` y `SELECT setval(...)` al final para evitar colisiones y ajustar secuencias — por lo tanto es idempotente y seguro para re-ejecuciones parciales.

Opción B — psql (recomendado para scripts)

```bash
# Exportar DATABASE_URL desde .env o reemplazar en línea
export DATABASE_URL="postgres://usuario:pass@host:port/dbname"

# Ejecutar respaldo (si aplica)
psql "$DATABASE_URL" -f respaldo.sql

# Ejecutar seed (idempotente)
psql "$DATABASE_URL" -f seed_initial_data.sql
```

4.3 Ajustar secuencias y verificación

Si su `seed_initial_data.sql` no incluyó `setval`, ejecute después de la importación:

```sql
-- En psql o PGAdmin
SELECT setval(pg_get_serial_sequence('usuario','id_usuario'), COALESCE((SELECT MAX(id_usuario) FROM usuario), 1), true);
-- Repetir para otras tablas con serials: producto, variante_producto, imagen_producto, bodega, servicio, etc.
```

Verifique integridad:

```sql
-- Conteos
SELECT COUNT(*) FROM usuario;
SELECT COUNT(*) FROM producto;
-- Revisar claves duplicadas (ejemplo)
SELECT id_proveedor, COUNT(*) FROM proveedor_pago GROUP BY id_proveedor HAVING COUNT(*)>1;
```

## 5. Despliegue en Render

5.1 Archivos y configuración

- `Procfile` (ejemplo): `web: uvicorn nailsnice.asgi:application --host 0.0.0.0 --port $PORT`
- `render.yaml` (si usa Infrastructure as Code para servicios en Render)
- `requirements.txt` debe contener `gunicorn`, `uvicorn`, `django-extensions`, `weasyprint` si usa reportes.

5.2 Variables de entorno (en el panel de Render)

- `DJANGO_SECRET_KEY` — obligatorio
- `DATABASE_URL` — cadena de Neon (asegúrese de que las IP y conexiones estén permitidas)
- `DJANGO_ALLOWED_HOSTS` — dominio de Render o `*` (temporal)
- `DEBUG` — `False` en producción

5.3 Build & Start commands

Build command (ejemplo):

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Start command (procfile tiene prioridad):

```bash
uvicorn nailsnice.asgi:application --host 0.0.0.0 --port $PORT
```

Nota: Render no proporciona apt packages por defecto. Para WeasyPrint y librerías nativas, use Docker (siguiente sección) o un servicio con soporte de paquetes.

## 6. Dependencias del sistema y WeasyPrint (reportes PDF)

WeasyPrint requiere librerías del sistema (Cairo, Pango, GDK, etc.). En Debian/Ubuntu instale:

```bash
sudo apt-get update
sudo apt-get install -y build-essential libpango1.0-0 libgdk-pixbuf2.0-0 libcairo2 libffi-dev libssl-dev shared-mime-info
```

Si despliega en Render, la forma más fiable es crear una imagen Docker que instale estas dependencias antes de instalar `requirements.txt`.

Ejemplo mínimo `Dockerfile`:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y build-essential libpango1.0-0 libgdk-pixbuf2.0-0 libcairo2 libffi-dev libssl-dev shared-mime-info && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV PYTHONUNBUFFERED=1
RUN python manage.py collectstatic --noinput
CMD ["uvicorn","nailsnice.asgi:application","--host","0.0.0.0","--port","$PORT"]
```

Consejo: probar localmente con `docker build -t nailsnice .` y `docker run -e PORT=8000 -p 8000:8000 nailsnice`.

## 7. Seeds: buenas prácticas y pasos seguros para Neon

- Use el `seed_initial_data.sql` del repo. Contiene `ON CONFLICT DO NOTHING` y sentencias `setval` para evitar colisiones.
- Siempre probar en una copia de la base (entorno staging) antes de ejecutar en producción.
- Comandos recomendados:

```bash
psql "$DATABASE_URL" -f seed_initial_data.sql
```

- Si se produce `duplicate key` aun con `ON CONFLICT`, revise qué columnas tienen constraints; ajustar la cláusula `ON CONFLICT (columna)` según el constraint.

## 8. Backups y restauración

Hacer backup antes de cambios en producción:

```bash
# Dump completo (plain SQL)
pg_dump "$DATABASE_URL" -Fc -f backup-$(date +%F).dump

# Restaurar (en otra DB de pruebas)
pg_restore -d postgres://user:pass@host:port/dbname backup-2026-06-17.dump
```

Para restaurar un dump SQL:

```bash
psql "$DATABASE_URL" -f respaldo.sql
```

## 9. Solución de errores comunes

- ERROR: duplicate key value violates unique constraint: Aplique `ON CONFLICT` o use `setval`/ajuste sequences; evitar insertar explicit `id` si el campo es serial.
- ERROR: column "es_activo" does not exist: Compare columnas en `respaldo.sql` y actualice `seed_initial_data.sql` para usar nombres reales.
- ModuleNotFoundError django_extensions: `pip install django-extensions` y agregar a `INSTALLED_APPS` si es necesario.
- DisallowedHost en Render: asegúrese de `DJANGO_ALLOWED_HOSTS` incluya el dominio de Render.
- WeasyPrint errores: faltan librerías nativas; instale paquetes del sistema o use Docker con deps nativas.
- Static files 404: ejecutar `python manage.py collectstatic` y configurar `STATIC_ROOT` y storage en Render.

Comandos de diagnóstico útiles:

```bash
python manage.py check
python manage.py showmigrations
psql "$DATABASE_URL" -c "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';"
```

## 10. Checklist post-despliegue

- [ ] Variables de entorno configuradas en Render
- [ ] `collectstatic` ejecutado
- [ ] Migraciones aplicadas contra la DB de Render
- [ ] Seeds ejecutados en staging y verificados
- [ ] Ajuste de secuencias (`setval`) verificado
- [ ] Supervisión y logs (Render / Sentry / Papertrail)

---

Si quieres, hago ahora:

- (A) Guardar este documento (he actualizado `PROYECTO_COMPLETO.md`), o moverlo a `docs/INSTALLATION.md`.
- (B) Crear un `Dockerfile` y `render.Dockerfile` listo para probar con WeasyPrint y publicar.
- (C) Ejecutar pasos de importación/validación en un entorno de prueba si me proporcionas las credenciales (no subir credenciales al repo).

Dime cuál opción prefieres y continúo.

# 🎉 Proyecto NailsNice Backend - Python (Django)

## ✅ Estado: COMPLETADO Y LISTO

Tu proyecto Django está 100% configurado, con BD MySQL conectada y datos iniciales cargados.

---

## 📁 Estructura Creada

```
C:\Users\juana\Nails_Nice_py/
├── venv/                          # Ambiente virtual Python
├── nailsnice/                     # Configuración principal Django
│   ├── settings.py               # Configuración (MySQL, CORS, apps)
│   ├── urls.py                   # Rutas principales
│   ├── asgi.py
│   └── wsgi.py
│
├── usuarios/                      # App 1: Usuarios, Auth, Roles
│   ├── models.py                 # Rol, Usuario, Empleado
│   ├── admin.py                  # Panel admin configurado
│   ├── views.py
│   └── migrations/
│
├── productos/                     # App 2: Productos y Catálogo
│   ├── models.py                 # Producto, Categoría, Marca, Color
│   ├── admin.py                  # Admin con filtros
│   └── migrations/
│
├── pedidos/                       # App 3: Pedidos y Ventas
│   ├── models.py                 # Pedido, Venta, Métodos Pago
│   ├── admin.py                  # Admin con inlines
│   └── migrations/
│
├── clientes/                      # App 4: Clientes
│   ├── models.py                 # Cliente, ServicioCliente
│   ├── admin.py
│   └── migrations/
│
├── servicios/                     # App 5: Servicios y Agendamiento
│   ├── models.py                 # Servicio, TipoServicio, Agendamiento
│   ├── admin.py
│   └── migrations/
│
├── core/                          # App 6: Utilidades
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py      # Comando para cargar datos iniciales
│   └── migrations/
│
├── manage.py                      # Gestor de Django
├── requirements.txt               # Dependencias Python
├── README.md                      # Documentación base
├── .env.example                   # Variables de entorno (ejemplo)
├── .gitignore                     # Archivos a ignorar en git
└── seed_roles.sql                 # Script SQL (referencia)
```

---

## 🚀 INICIAR EL SERVIDOR

### Opción 1: Terminal PowerShell (Windows)
```powershell
cd C:\Users\juana\Nails_Nice_py
.\venv\Scripts\Activate.ps1
python manage.py runserver 8000
```

### Opción 2: Terminal CMD
```cmd
cd C:\Users\juana\Nails_Nice_py
venv\Scripts\activate.bat
python manage.py runserver 8000
```

### Resultado esperado:
```
Starting development server at http://127.0.0.1:8000/
```

---

## 🔐 Credenciales de Acceso (Admin)

**Email:** `admin@nailsnice.com`  
**Password:** `Admin123!`

**Panel Admin:** http://localhost:8000/admin/

---

## 📊 Base de Datos MySQL

**Conexión (desde settings.py):**
- **Engine:** MySQL
- **BD:** `nails_nice`
- **Usuario:** `root`
- **Password:** (vacío o tu contraseña)
- **Host:** `localhost:3306`

**Tablas creadas:**
- `usuarios_rol` - Roles (Administrador, Cliente, Empleado)
- `usuarios_usuario` - Usuarios con auth personalizado
- `usuarios_empleado` - Empleados
- `productos_producto` - Catálogo de productos
- `productos_categoria` - Categorías
- `productos_marca` - Marcas
- `productos_color` - Colores
- `productos_unidadmedida` - Unidades de medida
- `pedidos_pedido` - Órdenes de compra
- `pedidos_venta` - Ventas registradas
- `clientes_cliente` - Información de clientes
- `clientes_serviciocliente` - Tickets y comunicación
- `servicios_servicio` - Servicios ofrecidos
- `servicios_agendamiento` - Agendamientos de citas

---

## 🛠️ Comandos Útiles

### Crear migraciones después de cambiar modelos
```bash
python manage.py makemigrations
python manage.py migrate
```

### Crear un nuevo usuario desde terminal
```bash
python manage.py createsuperuser
```

### Cargar datos iniciales
```bash
python manage.py seed_data
```

### Shell interactivo de Django
```bash
python manage.py shell

# Dentro del shell:
from usuarios.models import Usuario
usuarios = Usuario.objects.all()
print(usuarios)
```

### Crear una nueva app
```bash
python manage.py startapp nombre_app
```

---

## 🌐 CORS Configurado

Frontend puede consumir API desde:
- `http://localhost:3000`
- `http://localhost:8000`
- `http://localhost:8080`
- `http://127.0.0.1:3000`

**Para agregar más orígenes:**  
Editar `nailsnice/settings.py` → `CORS_ALLOWED_ORIGINS`

---

## 📝 Modelos Principales

### 1. **Usuarios**
- Usuario (custom, con email como USERNAME)
- Rol (Administrador, Cliente, Empleado)
- Empleado

### 2. **Productos**
- Producto (nombre, precio, estado)
- Categoría
- Marca
- Color
- UnidadMedida

### 3. **Pedidos**
- Pedido (cliente, estado, fecha)
- PedidoProducto (detalle)
- Venta
- DetalleVenta
- MetodoPago

### 4. **Clientes**
- Cliente (usuario, dirección, puntos fidelidad)
- ServicioCliente (tickets, comunicación)

### 5. **Servicios**
- Servicio (nombre, precio, duración)
- TipoServicio (Manicura, Pedicura, Maquillaje, etc.)
- Agendamiento (fecha, hora, estado)

---

## ⚙️ Configuración Django

### settings.py incluye:
✓ MySQL Database  
✓ JWT/Token Auth (lista para implementar)  
✓ CORS Headers  
✓ Django REST Framework  
✓ Spanish Language & Timezone  
✓ Custom User Model  
✓ Admin Personalizado  

### Validaciones incluidas:
✓ Email único  
✓ Precios mínimos (>0)  
✓ Cantidad válidas (>0)  
✓ Estados predefinidos  
✓ Relaciones con PROTECT/CASCADE  

---

## 🔄 Próximos Pasos Recomendados

1. **Crear Serializers (DRF)**
   - Crear `usuarios/serializers.py`
   - Crear `productos/serializers.py`
   - etc.

2. **Crear API ViewSets (DRF)**
   - CRUD endpoints para cada modelo
   - Filtros y búsquedas
   - Permisos basados en roles

3. **Implementar Autenticación**
   - JWT Tokens
   - Login/Register endpoints
   - Refresh tokens

4. **Conectar Frontend React**
   - Actualizar `apiBase` URL a `http://localhost:8000/api/`
   - Crear servicios para consumir endpoints

5. **Agregar Tests**
   - Unit tests para models
   - Integration tests para API

6. **Documentación API**
   - Swagger/OpenAPI con `drf-spectacular`

---

## 📚 Recursos

- **Django Docs:** https://docs.djangoproject.com/
- **DRF:** https://www.django-rest-framework.org/
- **MySQL Connector:** https://mysqlclient.readthedocs.io/

---

## 💡 Notas Importantes

- **Cambiar PASSWORD en settings.py** si tu usuario MySQL tiene contraseña
- **Cambiar SECRET_KEY** en producción (use `django-insecure-...` → variable env)
- **Configurar ALLOWED_HOSTS** antes de deploy
- **Nunca commitear .env** (usar .env.example)

---

## ✨ ¡LISTO PARA TRABAJAR!

Tu proyecto Django está totalmente funcional.  
Ahora puedes:
- Crear APIs REST con DRF
- Implementar autenticación
- Conectar el frontend React
- Agregar más lógica de negocio

**¡Vamos a hacerlo!** 🚀

