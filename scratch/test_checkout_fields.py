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
    print("Iniciando pruebas de verificación de campos en Checkout...")
    User = get_user_model()
    
    # 1. Limpieza
    User.objects.filter(correo='checkouttest@example.com').delete()
    
    # 2. Setup
    rol_cliente, _ = Rol.objects.get_or_create(
        nombre=Rol.CLIENTE,
        defaults={'descripcion': 'Cliente', 'es_sistema': True}
    )
    user = User.objects.create_user(
        correo='checkouttest@example.com',
        password='Password123!',
        nombre1='Ana',
        apellido1='Mongui',
        telefono='3123456789'
    )
    from clientes.models import Cliente
    cliente, _ = Cliente.objects.get_or_create(usuario=user)
    
    # Agregar dirección guardada
    dir_pred = DireccionUsuario.objects.create(
        usuario=user,
        tipo_direccion='ENVIO',
        etiqueta='Principal',
        nombre_destinatario='Ana Mongui',
        linea1='Calle 122 #15-30',
        linea2='Apto 301',
        ciudad='Bogota',
        departamento='Cundinamarca',
        es_predeterminada_envio=True,
        es_predeterminada_factura=True
    )
    
    # Crear carrito
    carrito = CarritoCompra.objects.create(cliente=cliente, estado='ACTIVO', id_cliente_activo=1)
    
    # Agregar un item al carrito en sesión (para el test de checkout)
    from productos.models import Producto, VarianteProducto
    from inventario.models import Bodega, SaldoInventario
    bodega, _ = Bodega.objects.get_or_create(nombre='Principal')
    prod = Producto.objects.create(nombre='Esmalte Rojo', estado='ACTIVO')
    var = VarianteProducto.objects.create(producto=prod, sku='ESM-ROJO', precio=Decimal('100.00'))
    
    # Asegurar stock
    SaldoInventario.objects.create(
        variante=var,
        bodega=bodega,
        cantidad_existencia=10,
        cantidad_reservada=0
    )
    
    client = Client()
    client.force_login(user)
    
    # Poner producto en carrito en sesión
    session = client.session
    session['cart'] = {str(var.id_variante): 1}
    session.save()
    
    # 3. GET Checkout
    response = client.get(reverse('checkout'))
    assert response.status_code == 200, f"Error GET checkout: {response.status_code}"
    html_content = response.content.decode('utf-8')
    
    # Verificar que los nuevos campos de dirección se pintan en el HTML
    assert 'name="linea1"' in html_content, "linea1 no está en el HTML"
    assert 'name="linea2"' in html_content, "linea2 no está en el HTML"
    assert 'name="ciudad"' in html_content, "ciudad no está en el HTML"
    assert 'name="departamento"' in html_content, "departamento no está en el HTML"
    assert 'id="usar-direccion-guardada"' in html_content, "checkbox de dirección guardada no está en el HTML"
    assert 'direccion-prefill-data' in html_content, "bloque de script de prefill no está en el HTML"
    
    print("Prueba de GET de Checkout Exitosa.")
    
    # 4. POST Checkout con dirección inválida
    from inventario.models import TipoMovimientoInventario
    TipoMovimientoInventario.objects.filter(codigo='SALIDA_VENTA').delete()

    post_data_invalid = {
        'linea1': 'Mi casa 123', # Formato inválido
        'linea2': '',
        'ciudad': 'Bogota',
        'departamento': 'Cundinamarca',
        'metodo_pago': 'contraentrega'
    }
    response = client.post(reverse('checkout'), post_data_invalid)
    # Debe rechazar y redirigir con error (o renderizar con errores)
    # Dado que no es AJAX, redirige o da error de validación
    # Debería dar un mensaje de error de formato colombiano
    # Vamos a verificarlo vía AJAX
    response_ajax = client.post(
        reverse('checkout'),
        post_data_invalid,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response_ajax.status_code == 400, "Se esperaba error 400 por dirección inválida"
    data = response_ajax.json()
    assert 'Usa un formato de vía colombiano' in data['error'], f"Mensaje incorrecto: {data['error']}"
    print("Prueba de validación estricta de dirección Exitosa.")
    
    # 5. POST Checkout con dirección válida
    post_data_valid = {
        'linea1': 'Calle 100 #20-30',
        'linea2': 'Torre C Apto 402',
        'ciudad': 'Medellin',
        'departamento': 'Antioquia',
        'metodo_pago': 'contraentrega'
    }
    response_ajax_ok = client.post(
        reverse('checkout'),
        post_data_valid,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    assert response_ajax_ok.status_code == 200, f"Error POST checkout válido: {response_ajax_ok.content}"
    ok_data = response_ajax_ok.json()
    assert ok_data['ok'] is True
    assert 'factura_url' in ok_data
    
    # Verificar en la base de datos que el pedido se guardó con la dirección separada y se sincronizó en el perfil
    pedido = PedidoVenta.objects.latest('id_pedido')
    assert pedido.direccion_envio.linea1 == 'Calle 100 #20-30'
    assert pedido.direccion_envio.linea2 == 'Torre C Apto 402'
    assert pedido.direccion_envio.ciudad == 'Medellin'
    assert pedido.direccion_envio.departamento == 'Antioquia'
    
    # Verificar perfil sincronizado
    dir_updated = DireccionUsuario.objects.get(usuario=user, es_predeterminada_envio=True)
    assert dir_updated.linea1 == 'Calle 100 #20-30'
    assert dir_updated.linea2 == 'Torre C Apto 402'
    assert dir_updated.ciudad == 'Medellin'
    assert dir_updated.departamento == 'Antioquia'
    assert TipoMovimientoInventario.objects.filter(codigo='SALIDA_VENTA').exists()
    print("Tipo de movimiento SALIDA_VENTA auto-creado exitosamente en base de datos.")
    print("Prueba de POST y sincronización de Checkout Exitosa.")
    
    # Limpieza final
    User.objects.filter(correo='checkouttest@example.com').delete()
    prod.delete()
    print("Todas las verificaciones de Checkout pasaron exitosamente.")

if __name__ == '__main__':
    run_tests()
