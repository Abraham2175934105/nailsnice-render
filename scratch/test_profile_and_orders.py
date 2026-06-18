import os
import django
import sys

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nailsnice.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from usuarios.models import Rol
from clientes.models import DireccionUsuario
from pedidos.models import PedidoVenta, CarritoCompra
from decimal import Decimal

def run_tests():
    print("Iniciando pruebas de verificación de Perfil y Pedidos...")
    User = get_user_model()
    
    # 1. Limpieza de datos anteriores de prueba si existen
    User.objects.filter(correo='perfiltest@example.com').delete()
    
    # 2. Crear rol y usuario de prueba
    rol_cliente, _ = Rol.objects.get_or_create(
        nombre=Rol.CLIENTE,
        defaults={'descripcion': 'Cliente', 'es_sistema': True}
    )
    
    user = User.objects.create_user(
        correo='perfiltest@example.com',
        password='Password123!',
        nombre1='Ana',
        apellido1='Mongui',
        telefono='3123456789'
    )
    
    # Asociar perfil cliente
    from clientes.models import Cliente
    cliente, _ = Cliente.objects.get_or_create(usuario=user)
    
    # 3. Crear dirección predeterminada
    dir_pred = DireccionUsuario.objects.create(
        usuario=user,
        tipo_direccion='ENVIO',
        etiqueta='Principal',
        nombre_destinatario='Ana Mongui',
        linea1='Calle 122 #15-30',
        ciudad='Bogota',
        departamento='Cundinamarca',
        es_predeterminada_envio=True,
        es_predeterminada_factura=True
    )
    
    # 4. Crear un pedido de prueba
    carrito = CarritoCompra.objects.create(cliente=cliente, estado='COMPLETADO', id_cliente_activo=1)
    
    pedido = PedidoVenta.objects.create(
        cliente=cliente,
        estado='PAGADO',
        subtotal=Decimal('100.00'),
        monto_total=Decimal('100.00'),
        direccion_envio=dir_pred
    )
    
    # Asociar detalle al pedido
    from productos.models import Producto, VarianteProducto
    from inventario.models import Bodega
    
    bodega, _ = Bodega.objects.get_or_create(nombre='Principal')
    prod = Producto.objects.create(nombre='Esmalte Rojo', estado='ACTIVO')
    var = VarianteProducto.objects.create(producto=prod, sku='ESM-ROJO', precio=Decimal('100.00'))
    
    from pedidos.models import DetallePedidoVenta
    DetallePedidoVenta.objects.create(
        pedido=pedido,
        variante=var,
        nombre_producto_snapshot='Esmalte Rojo',
        sku_snapshot='ESM-ROJO',
        cantidad=1,
        precio_unitario=Decimal('100.00'),
        total_linea=Decimal('100.00')
    )
    
    # 5. Instanciar cliente de prueba y autenticarse
    client = Client()
    client.force_login(user)
    
    # 6. Realizar petición GET al perfil
    response = client.get(reverse('perfil'))
    assert response.status_code == 200, f"Error GET perfil: {response.status_code}"
    
    html_content = response.content.decode('utf-8')
    
    # Verificar que la dirección y pedidos están en el contexto
    assert 'direccion' in response.context, "La dirección no está en el contexto."
    assert 'pedidos' in response.context, "Los pedidos no están en el contexto."
    
    direccion_ctx = response.context['direccion']
    pedidos_ctx = response.context['pedidos']
    
    assert direccion_ctx.linea1 == 'Calle 122 #15-30', f"Dirección incorrecta: {direccion_ctx.linea1}"
    assert len(pedidos_ctx) == 1, f"Se esperaba 1 pedido, se obtuvo: {len(pedidos_ctx)}"
    
    pedido_ctx = pedidos_ctx[0]
    assert pedido_ctx['precio'] == Decimal('100.00'), f"Precio incorrecto: {pedido_ctx['precio']}"
    assert pedido_ctx['producto'] == 'Esmalte Rojo', f"Producto incorrecto: {pedido_ctx['producto']}"
    assert pedido_ctx['cantidad'] == 1, f"Cantidad incorrecta: {pedido_ctx['cantidad']}"
    
    # Verificar que los campos se pinten en el HTML
    assert 'Calle 122 #15-30' in html_content, "La dirección principal no se pinta en el HTML"
    assert 'Bogota' in html_content, "La ciudad no se pinta en el HTML"
    assert 'Cundinamarca' in html_content, "El departamento no se pinta en el HTML"
    assert 'Esmalte Rojo' in html_content, "El nombre del producto del pedido no se pinta en el HTML"
    
    print("Prueba de GET de Perfil Exitosa.")
    
    # 7. Realizar petición POST para actualizar perfil y dirección
    post_data = {
        'action': 'update_profile',
        'nombre': 'Anabella',
        'apellido': 'Mongui',
        'telefono': '3123456780',
        'linea1': 'Calle 100 #20-30',
        'ciudad': 'Medellin',
        'departamento': 'Antioquia',
        'password_actual': 'Password123!'
    }
    
    response = client.post(reverse('perfil'), post_data)
    assert response.status_code in [200, 302], f"Error POST perfil: {response.status_code}"
    
    # Verificar en la base de datos
    user.refresh_from_db()
    assert user.nombre == 'Anabella', f"Nombre no actualizado: {user.nombre}"
    
    dir_updated = DireccionUsuario.objects.get(usuario=user, es_predeterminada_envio=True)
    assert dir_updated.linea1 == 'Calle 100 #20-30', f"Dirección no actualizada: {dir_updated.linea1}"
    assert dir_updated.ciudad == 'Medellin', f"Ciudad no actualizada: {dir_updated.ciudad}"
    assert dir_updated.departamento == 'Antioquia', f"Departamento no actualizado: {dir_updated.departamento}"
    
    print("Prueba de POST de actualización de Perfil Exitosa.")
    
    # Limpieza final
    User.objects.filter(correo='perfiltest@example.com').delete()
    prod.delete()
    print("Todas las verificaciones pasaron exitosamente.")

if __name__ == '__main__':
    run_tests()
