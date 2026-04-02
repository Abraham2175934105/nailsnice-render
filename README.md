# NailsNice Backend - Python (Django)

Proyecto de migración de **NailsNice** de Java/Spring Boot a Python/Django.

## 📋 Estructura del Proyecto

```
nailsnice_py/
├── nailsnice/           # Configuración principal
│   ├── settings.py      # Configuración de Django
│   ├── urls.py          # Rutas principales
│   └── wsgi.py
├── usuarios/            # App: Gestión de usuarios y autenticación
├── productos/           # App: Productos y categorías
├── pedidos/             # App: Pedidos y carritos
├── clientes/            # App: Información de clientes
├── servicios/           # App: Servicios y agendamiento
├── core/                # App: Utilidades y funciones base
├── manage.py
└── venv/
```

## 🚀 Instalación y Setup

### 1. Activar el Ambiente Virtual
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
```

### 4. Crear/Migrar Base de Datos
```bash
python manage.py migrate
```

### 5. Crear Superusuario (Admin)
```bash
python manage.py createsuperuser
```

### 6. Ejecutar Servidor
```bash
python manage.py runserver 8000
```

El servidor estará disponible en: `http://localhost:8000/`

## 📚 Apps Principales

### 1. **usuarios** - Gestión de usuarios
- Modelos: User, Rol, Permisos
- Endpoints: Login, Register, Perfil, Cambiar contraseña

### 2. **productos** - Catálogo de productos
- Modelos: Producto, Categoría, Color, Marca, UnidadMedida
- Endpoints: CRUD productos, filtros por categoría/marca

### 3. **pedidos** - Órdenes y carritos
- Modelos: Pedido, DetallePedido, Venta, DetalleVenta
- Endpoints: Crear orden, listar, cancelar

### 4. **clientes** - Información de clientes
- Modelos: Cliente, Dirección, ServicioCliente
- Endpoints: Perfil cliente, historial, puntos fidelidad

### 5. **servicios** - Servicios y agendamiento
- Modelos: Servicio, TipoServicio, Agendamiento
- Endpoints: Listar servicios, agendar, historial

## 🔐 Seguridad y Validaciones

- Autenticación con JWT (Token)
- Permisos basados en roles
- Validacion de campos en formularios
- CORS habilitado para localhost
- SQL Injection protegido (ORM Django)

## 🛠️ Desarrollo

### Crear migraciones
```bash
python manage.py makemigrations
```

### Aplicar migraciones
```bash
python manage.py migrate
```

### Crear superficies admin
```bash
python manage.py createsuperuser
```

### Panel Admin
Acceder a: `http://localhost:8000/admin/`

## 📝 Notas

- Proyecto en desarrollo (MVP)
- Base de datos: MySQL
- Frontend sugerido: React/Vite (conectar a API REST)
- API documentada con DRF Swagger (próximamente)

## 👤 Autor

Migración realizado con GitHub Copilot
