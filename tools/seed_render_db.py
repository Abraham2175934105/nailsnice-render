import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta


def main():
    # Accept DATABASE_URL from env or first CLI arg
    db_url = os.environ.get('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not db_url:
        print('ERROR: please provide DATABASE_URL as env var or first arg')
        sys.exit(2)

    os.environ.setdefault('DATABASE_URL', db_url)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Profesional Beauty.settings')

    import django
    django.setup()

    from django.utils import timezone
    from usuarios.models import Usuario, RolAcceso, UsuarioRol
    from clientes.models import Cliente, DireccionUsuario, TipoMetodoPago, ProveedorPago, MetodoPagoCliente
    from productos.models import MarcaCatalogo, CategoriaCatalogo, SubcategoriaCatalogo, Producto, VarianteProducto
    from inventario.models import Bodega, SaldoInventario, MovimientoInventario, TipoMovimientoInventario, ItemMovimientoInventario
    from servicios.models import TipoServicio, CategoriaServicio, Servicio, EmpleadoServicio, Agendamiento
    from pedidos.models import CarritoCompra, ItemCarritoCompra, PedidoVenta, DetallePedidoVenta
    from django.contrib.auth.hashers import make_password

    print('Connected. Seeding data...')

    # Roles
    rol_admin, _ = RolAcceso.objects.get_or_create(codigo='ADMIN', defaults={'nombre': 'Administrador', 'es_sistema': True})
    rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', defaults={'nombre': 'Cliente'})
    rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', defaults={'nombre': 'Empleado'})

    # Superuser
    admin_email = 'admin@Profesional Beauty.com'
    admin_password = '12345678Ns.'
    admin, created = Usuario.objects.get_or_create(correo=admin_email, defaults={'nombre': 'Administrador', 'apellido': 'Nails', 'is_staff': True, 'is_superuser': True, 'estado': 'ACTIVO'})
    if created:
        admin.set_password(admin_password)
        admin.save()
        UsuarioRol.objects.get_or_create(id_usuario=admin, id_rol=rol_admin)
        print('Created superuser', admin_email)
    else:
        print('Superuser already exists')

    # Create 5 empleados (as usuarios with role EMPLEADO)
    empleados = []
    for i in range(1, 3):
        correo = f'tecnico{i}@Profesional Beauty.com'
        u, created = Usuario.objects.get_or_create(correo=correo, defaults={'nombre': f'Tecnico{i}', 'apellido': 'Nails', 'estado': 'ACTIVO'})
        if created:
            u.set_password(admin_password)
            u.save()
            UsuarioRol.objects.get_or_create(id_usuario=u, id_rol=rol_empleado)
        empleados.append(u)

    # Create 5 clientes
    clientes = []
    for i in range(1, 6):
        correo = f'cliente{i}@example.com'
        u, created = Usuario.objects.get_or_create(correo=correo, defaults={'nombre': f'Cliente{i}', 'apellido': 'Prueba'})
        if created:
            u.set_password(admin_password)
            u.save()
            UsuarioRol.objects.get_or_create(id_usuario=u, id_rol=rol_cliente)
        cliente, _ = Cliente.objects.get_or_create(usuario=u)
        # address
        DireccionUsuario.objects.get_or_create(usuario=u, tipo_direccion=DireccionUsuario.TIPO_ENVIO, nombre_destinatario=u.nombre, linea1=f'Calle {i} # {10+i}', ciudad='Bogota', etiqueta=f'Casa {i}', es_predeterminada_envio=True)
        clientes.append(cliente)

    # Productos: marca, categoria, subcategoria, producto, variante
    marca, _ = MarcaCatalogo.objects.get_or_create(nombre='Profesional Beauty')
    categoria, _ = CategoriaCatalogo.objects.get_or_create(nombre='Productos de Uñas', slug='productos-unas')
    subcat, _ = SubcategoriaCatalogo.objects.get_or_create(categoria=categoria, nombre='Esmaltes', slug='esmaltes')

    variantes = []
    for i in range(1, 6):
        prod, _ = Producto.objects.get_or_create(subcategoria=subcat, nombre=f'Esmalte Color {i}', slug=f'esmalte-color-{i}', defaults={'marca': marca, 'descripcion_corta': 'Esmalte de alta duración'})
        var, _ = VarianteProducto.objects.get_or_create(producto=prod, sku=f'ENSK-{1000+i}', defaults={'precio': Decimal('12900.00'), 'costo': Decimal('6000.00')})
        variantes.append(var)

    # Inventario: bodega + saldos
    bodega, _ = Bodega.objects.get_or_create(codigo='B1', defaults={'nombre': 'Bodega Principal'})
    for v in variantes:
        SaldoInventario.objects.update_or_create(variante=v, defaults={'bodega': bodega, 'cantidad_existencia': 20, 'cantidad_reservada': 0, 'nivel_reorden': 5})

    # Servicios: tipo, categoria, servicio
    tipo_serv, _ = TipoServicio.objects.get_or_create(codigo='SERV_MANI', defaults={'nombre': 'Manicura'})
    cat_serv, _ = CategoriaServicio.objects.get_or_create(nombre='Manicura & Pedicura')
    servicio_objs = []
    for i in range(1, 6):
        s, _ = Servicio.objects.get_or_create(tipo_servicio=tipo_serv, categoria_servicio=cat_serv, nombre=f'Manicura Express {i}', defaults={'duracion_minutos': 30, 'precio_base': Decimal('45000.00')})
        servicio_objs.append(s)

    # Assign servicios to empleados
    for emp in empleados:
        for s in servicio_objs[:2]:
            EmpleadoServicio.objects.get_or_create(empleado=emp.empleado, servicio=s)

    # Pedidos: create carrito + pedido + detalles
    for idx, cliente in enumerate(clientes, start=1):
        carrito = CarritoCompra.objects.create(cliente=cliente, estado='ACTIVO')
        pedido = PedidoVenta.objects.create(cliente=cliente, carrito=carrito, estado='PAGADO', subtotal=Decimal('12900.00') * 1, monto_total=Decimal('12900.00'))
        det = DetallePedidoVenta.objects.create(pedido=pedido, variante=variantes[idx-1], nombre_producto_snapshot=variantes[idx-1].producto.nombre, sku_snapshot=variantes[idx-1].sku, cantidad=1, precio_unitario=variantes[idx-1].precio, total_linea=variantes[idx-1].precio)

    print('Seeding completed:')
    print('Usuarios:', Usuario.objects.count())
    print('Clientes:', Cliente.objects.count())
    print('Productos:', Producto.objects.count())
    print('Variantes:', VarianteProducto.objects.count())
    print('Servicios:', Servicio.objects.count())
    print('Pedidos:', PedidoVenta.objects.count())


if __name__ == '__main__':
    main()
