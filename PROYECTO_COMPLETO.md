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

