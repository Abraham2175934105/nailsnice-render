from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from core.models import AuditLog
from clientes.models import Cliente, DireccionUsuario
from inventario.models import Bodega, SaldoInventario, TipoMovimientoInventario, ItemMovimientoInventario
from productos.models import MarcaCatalogo, CategoriaCatalogo, SubcategoriaCatalogo, Producto, VarianteProducto
from usuarios.models import Rol

from .models import DetallePedidoVenta, PedidoVenta
from .services import create_pedido_from_cart


_SEQ = count(1)


def _next_seq():
    return next(_SEQ)


def make_rol(nombre):
    rol, _ = Rol.objects.get_or_create(nombre=nombre)
    return rol

def make_user(email='user@test.com', rol_nombre=None, is_superuser=False, telefono=''):
    rol = make_rol(rol_nombre or Rol.CLIENTE)
    return get_user_model().objects.create_user(
        email=email,
        password='Pwd12345!',
        id_rol=rol,
        nombre1='Test',
        is_superuser=is_superuser,
        telefono=telefono,
    )

def make_admin(email='admin@test.com'):
    return make_user(email=email, rol_nombre=Rol.ADMIN, is_superuser=True)

def make_empleado(email='empleado@test.com', telefono='3001234567'):
    return make_user(email=email, rol_nombre=Rol.EMPLEADO, telefono=telefono)

def ensure_salida_movimiento():
    tipo = TipoMovimientoInventario.objects.filter(codigo='SALIDA_VENTA').first()
    if tipo:
        return tipo
    return TipoMovimientoInventario.objects.create(
        id_tipo_movimiento=1,
        codigo='SALIDA_VENTA',
        descripcion='Salida venta',
        direccion=-1,
    )


def make_bodega():
    bodega, _ = Bodega.objects.get_or_create(
        codigo='BOD-TEST',
        defaults={'nombre': 'Bodega Test', 'ciudad': 'Bogota'},
    )
    return bodega


def make_variante(stock=5, precio=Decimal('10000'), activo=True):
    seq = _next_seq()
    categoria = CategoriaCatalogo.objects.create(nombre=f"Cat {seq}", slug=f"cat-{seq}")
    subcategoria = SubcategoriaCatalogo.objects.create(
        categoria=categoria,
        nombre=f"Sub {seq}",
        slug=f"sub-{seq}",
    )
    marca = MarcaCatalogo.objects.create(nombre=f"Marca {seq}")
    producto = Producto.objects.create(
        subcategoria=subcategoria,
        marca=marca,
        nombre=f"Prod {seq}",
        slug=f"prod-{seq}",
        estado='ACTIVO',
    )
    variante = VarianteProducto.objects.create(
        producto=producto,
        sku=f"SKU-{seq}",
        precio=precio,
        costo=Decimal('0'),
        activo=activo,
    )
    bodega = make_bodega()
    SaldoInventario.objects.update_or_create(
        variante=variante,
        defaults={
            'bodega': bodega,
            'cantidad_existencia': stock,
            'cantidad_reservada': 0,
        },
    )
    return variante


def make_cliente(usuario):
    return Cliente.objects.create(usuario=usuario)


def make_direccion(usuario, linea1='Calle 1', ciudad='Bogota', nombre_destinatario='Test'):
    return DireccionUsuario.objects.create(
        usuario=usuario,
        tipo_direccion='ENVIO',
        etiqueta='Test',
        nombre_destinatario=nombre_destinatario,
        linea1=linea1,
        ciudad=ciudad,
        codigo_pais='CO',
        es_predeterminada_envio=True,
        es_predeterminada_factura=False,
    )


def make_pedido(cliente, direccion, total=Decimal('10000'), estado='PENDIENTE_PAGO'):
    return PedidoVenta.objects.create(
        numero_pedido='',
        cliente=cliente,
        estado=estado,
        subtotal=total,
        monto_envio=Decimal('0'),
        monto_impuesto=Decimal('0'),
        monto_descuento=Decimal('0'),
        monto_total=total,
        direccion_envio=direccion,
    )


class PedidoModelUnitTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.cliente = make_cliente(self.user)
        self.direccion = make_direccion(self.user)

    def test_pedido_str_contiene_id_y_usuario(self):
        pedido = make_pedido(self.cliente, self.direccion, total=Decimal('10000'))
        self.assertIn(str(pedido.id_pedido), str(pedido))

    def test_estado_default_es_pendiente(self):
        pedido = make_pedido(self.cliente, self.direccion, total=Decimal('5000'))
        self.assertEqual(pedido.estado, 'PENDIENTE_PAGO')

    def test_total_se_almacena_como_decimal(self):
        pedido = make_pedido(self.cliente, self.direccion, total=Decimal('19999.99'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.monto_total, Decimal('19999.99'))


class PedidosLegacyModelUnitTest(TestCase):

    def test_manager_activos_excluye_inactivos(self):
        user = make_user('a@test.com')
        cliente = make_cliente(user)
        direccion = make_direccion(user)
        make_pedido(cliente, direccion, estado='PAGADO')
        make_pedido(cliente, direccion, estado='CANCELADO')
        estados = list(PedidoVenta.objects.filter(estado='PAGADO').values_list('estado', flat=True))
        self.assertIn('PAGADO', estados)
        self.assertNotIn('CANCELADO', estados)

    def test_pedido_legacy_str_no_lanza_error(self):
        user = make_user('str@test.com')
        cliente = make_cliente(user)
        direccion = make_direccion(user)
        pedido = make_pedido(cliente, direccion)
        self.assertIsInstance(str(pedido), str)


class DetallePedidoModelUnitTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.variante = make_variante(precio=Decimal('5000'))
        self.cliente = make_cliente(self.user)
        self.direccion = make_direccion(self.user)
        self.pedido = make_pedido(self.cliente, self.direccion, total=Decimal('10000'))

    def test_subtotal_es_precio_por_cantidad(self):
        detalle = DetallePedidoVenta.objects.create(
            pedido=self.pedido,
            variante=self.variante,
            nombre_producto_snapshot=self.variante.producto.nombre,
            sku_snapshot=self.variante.sku,
            cantidad=3,
            precio_unitario=Decimal('5000'),
        )
        self.assertEqual(detalle.subtotal(), Decimal('15000'))

    def test_cantidad_minima_es_1(self):
        detalle = DetallePedidoVenta.objects.create(
            pedido=self.pedido,
            variante=self.variante,
            nombre_producto_snapshot=self.variante.producto.nombre,
            sku_snapshot=self.variante.sku,
            cantidad=1,
            precio_unitario=Decimal('5000'),
        )
        self.assertEqual(detalle.cantidad, 1)


class PedidoServiceUnitTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.variante = make_variante(stock=2, precio=Decimal('5000'))
        ensure_salida_movimiento()

    def test_service_valida_stock_insuficiente(self):
        items = [{'variante': self.variante, 'cantidad': 5}]
        with self.assertRaises(ValidationError):
            create_pedido_from_cart(self.user, items, {'linea1': 'Calle 1', 'ciudad': 'Bogota'}, 'contraentrega')

    def test_service_valida_tipo_movimiento_existente(self):
        TipoMovimientoInventario.objects.all().delete()
        items = [{'variante': self.variante, 'cantidad': 1}]
        with self.assertRaises(ValidationError):
            create_pedido_from_cart(self.user, items, {'linea1': 'Calle 1', 'ciudad': 'Bogota'}, 'contraentrega')

    def test_service_calcula_total_correctamente(self):
        items = [{'variante': self.variante, 'cantidad': 2}]
        pedido = create_pedido_from_cart(self.user, items, {'linea1': 'Calle 1', 'ciudad': 'Bogota'}, 'contraentrega')
        self.assertEqual(pedido.monto_total, Decimal('10000'))

    def test_service_crea_audit_log(self):
        items = [{'variante': self.variante, 'cantidad': 1}]
        pedido = create_pedido_from_cart(self.user, items, {'linea1': 'Calle 1', 'ciudad': 'Bogota'}, 'contraentrega')
        self.assertTrue(
            AuditLog.objects.filter(
                action='pedidos.create', object_id=str(pedido.id_pedido)
            ).exists()
        )


class CarritoFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.variante = make_variante(stock=5)

    def test_agregar_al_carrito_exitoso(self):
        self.client.force_login(self.user)
        url = reverse('carrito_agregar', args=[self.variante.id_variante])
        resp = self.client.post(url, {'cantidad': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('ok'))

    def test_agregar_al_carrito_actualiza_sesion(self):
        self.client.force_login(self.user)
        url = reverse('carrito_agregar', args=[self.variante.id_variante])
        self.client.post(url, {'cantidad': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        session_cart = self.client.session.get('cart', {})
        self.assertEqual(session_cart.get(str(self.variante.id_variante)), 1)

    def test_agregar_stock_insuficiente_retorna_400(self):
        self.client.force_login(self.user)
        SaldoInventario.objects.filter(variante=self.variante).update(cantidad_existencia=1)
        url = reverse('carrito_agregar', args=[self.variante.id_variante])
        resp = self.client.post(url, {'cantidad': 5}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json().get('ok'))
        self.assertIn('stock', resp.json().get('error', '').lower())

    def test_agregar_producto_inactivo_retorna_404(self):
        self.client.force_login(self.user)
        self.variante.activo = False
        self.variante.save(update_fields=['activo'])
        url = reverse('carrito_agregar', args=[self.variante.id_variante])
        resp = self.client.post(url, {'cantidad': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 404)

    def test_no_autenticado_redirige(self):
        url = reverse('carrito_agregar', args=[self.variante.id_variante])
        resp = self.client.post(url, {'cantidad': 1})
        self.assertIn(resp.status_code, [302, 401])


class CheckoutFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()
        self.client.force_login(self.user)

    def _set_cart(self, cantidad=2):
        session = self.client.session
        session['cart'] = {str(self.variante.id_variante): cantidad}
        session.save()

    def test_checkout_contraentrega_redirige(self):
        self._set_cart()
        resp = self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        self.assertEqual(resp.status_code, 302)

    def test_checkout_producto_inactivo_redirige_al_carrito(self):
        self.variante.activo = False
        self.variante.save(update_fields=['activo'])
        self._set_cart()
        resp = self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123',
            'ciudad': 'Bogota',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('carrito'))
        self.assertEqual(PedidoVenta.objects.count(), 0)

    def test_checkout_prerrellena_direccion_desde_cliente(self):
        DireccionUsuario.objects.create(
            usuario=self.user,
            tipo_direccion='ENVIO',
            etiqueta='Prefill',
            nombre_destinatario='Test',
            linea1='Calle 55 #10-20',
            ciudad='Bogota',
            codigo_pais='CO',
            es_predeterminada_envio=True,
        )
        self._set_cart()
        resp = self.client.get(reverse('checkout'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['direccion_prefill']['linea1'], 'Calle 55 #10-20')

    def test_checkout_prerrellena_ultima_direccion_no_predeterminada(self):
        DireccionUsuario.objects.create(
            usuario=self.user,
            tipo_direccion='ENVIO',
            etiqueta='Old',
            nombre_destinatario='Test',
            linea1='Calle 10 #20-30',
            ciudad='Bogota',
            codigo_pais='CO',
            es_predeterminada_envio=False,
        )
        DireccionUsuario.objects.create(
            usuario=self.user,
            tipo_direccion='ENVIO',
            etiqueta='New',
            nombre_destinatario='Test',
            linea1='Carrera 9 #80-11',
            ciudad='Bogota',
            codigo_pais='CO',
            es_predeterminada_envio=False,
        )
        self._set_cart()
        resp = self.client.get(reverse('checkout'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['direccion_prefill']['linea1'], 'Carrera 9 #80-11')

    def test_checkout_tarjeta_invalida_retorna_400_ajax(self):
        self._set_cart(1)
        resp = self.client.post(reverse('checkout'), {
            'metodo_pago': 'tarjeta',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
            'card_holder': 'Juan Perez',
            'card_number': '4111 1111 1111 1112',
            'card_expiry': '12/50',
            'card_cvv': '123',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json().get('ok'))
        self.assertIn('tarjeta', resp.json().get('error', '').lower())

    def test_checkout_tarjeta_valida_crea_pedido_ajax(self):
        self._set_cart(1)
        resp = self.client.post(reverse('checkout'), {
            'metodo_pago': 'tarjeta',
            'direccion': 'Carrera 55 #12-30',
            'ciudad': 'Bogota',
            'card_holder': 'Juan Perez',
            'card_number': '4111 1111 1111 1111',
            'card_expiry': '12/50',
            'card_cvv': '123',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('ok'))
        self.assertEqual(PedidoVenta.objects.count(), 1)


class LegacyAdminFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.user = make_user('user2@test.com')
        self.cliente = make_cliente(self.user)
        self.direccion = make_direccion(self.user)
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()
        self.pedido = make_pedido(self.cliente, self.direccion)

    def test_no_admin_redirigido(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('lista_pedidos'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_admin_accede_a_lista(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('lista_pedidos'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_crea_pedido_legacy_redirige(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse('crear_pedido'), {
            'cliente': self.cliente.pk,
            'variante': self.variante.pk,
            'cantidad': 1,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        })
        self.assertEqual(resp.status_code, 302)


class EmpleadoPedidosFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.emp1 = make_empleado('emp1@test.com', telefono='3001234567')
        self.emp2 = make_empleado('emp2@test.com', telefono='3007654321')
        self.cliente_emp1 = make_cliente(self.emp1)
        self.cliente_emp2 = make_cliente(self.emp2)
        self.direccion_emp1 = make_direccion(self.emp1)
        self.direccion_emp2 = make_direccion(self.emp2)
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()
        self.pedido_emp1 = make_pedido(self.cliente_emp1, self.direccion_emp1)
        self.pedido_emp2 = make_pedido(self.cliente_emp2, self.direccion_emp2)

    def test_empleado_solo_ve_sus_pedidos(self):
        self.client.force_login(self.emp1)
        resp = self.client.get(reverse('empleado_pedidos'))
        self.assertEqual(resp.status_code, 200)
        ids = [p.id_pedido for p in resp.context['pedidos']]
        self.assertIn(self.pedido_emp1.id_pedido, ids)
        self.assertNotIn(self.pedido_emp2.id_pedido, ids)

    def test_empleado_no_puede_editar_pedido_ajeno(self):
        self.client.force_login(self.emp1)
        resp = self.client.get(reverse('empleado_editar_pedido', args=[self.pedido_emp2.id_pedido]))
        self.assertEqual(resp.status_code, 404)

    def test_empleado_crear_pedido_asigna_su_email(self):
        self.client.force_login(self.emp1)
        resp = self.client.post(reverse('empleado_crear_pedido'), {
            'variante': self.variante.pk,
            'cantidad': 2,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        })
        self.assertEqual(resp.status_code, 302)
        nuevo = PedidoVenta.objects.order_by('-id_pedido').first()
        self.assertEqual(nuevo.cliente.usuario.correo, self.emp1.correo)

    def test_empleado_crear_pedido_hereda_telefono_de_perfil(self):
        self.client.force_login(self.emp1)
        self.client.post(reverse('empleado_crear_pedido'), {
            'variante': self.variante.pk,
            'cantidad': 2,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        })
        nuevo = PedidoVenta.objects.order_by('-id_pedido').first()
        self.assertEqual(nuevo.cliente.usuario.telefono, '3001234567')


class EmpleadoValidacionFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.emp = make_empleado('emp.val@test.com', telefono='3003332211')
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()
        self.client.force_login(self.emp)

    def _post_pedido(self, **overrides):
        payload = {
            'variante': self.variante.pk,
            'cantidad': 1,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        }
        payload.update(overrides)
        return self.client.post(reverse('empleado_crear_pedido'), payload)

    def test_direccion_invalida_muestra_errores(self):
        resp = self._post_pedido(direccion_linea1='Direccion sin formato')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'La dirección debe seguir un formato colombiano válido')
        self.assertContains(resp, 'Revisa los campos antes de guardar')
        self.assertEqual(PedidoVenta.objects.count(), 0)

    def test_cantidad_cero_muestra_error(self):
        resp = self._post_pedido(cantidad=0)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('cantidad', resp.context['form'].errors)

    def test_cantidad_negativa_muestra_error(self):
        resp = self._post_pedido(cantidad=-5)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('cantidad', resp.context['form'].errors)

    def test_precio_vacio_no_crea_pedido(self):
        resp = self._post_pedido(cantidad='')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PedidoVenta.objects.count(), 0)


class CheckoutIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.variante = make_variante(stock=5, precio=Decimal('10000'))
        ensure_salida_movimiento()
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.variante.id_variante): 2}
        session.save()

    def test_checkout_crea_pedido_en_bd(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        self.assertEqual(PedidoVenta.objects.count(), 1)

    def test_checkout_calcula_total_correcto(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        pedido = PedidoVenta.objects.first()
        self.assertEqual(pedido.monto_total, Decimal('20000'))

    def test_checkout_crea_detalle_pedido(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        self.assertEqual(DetallePedidoVenta.objects.count(), 1)
        detalle = DetallePedidoVenta.objects.first()
        self.assertEqual(detalle.cantidad, 2)
        self.assertEqual(detalle.variante.id_variante, self.variante.id_variante)

    def test_checkout_descuenta_stock(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        self.assertTrue(ItemMovimientoInventario.objects.filter(variante=self.variante).exists())

    def test_checkout_limpia_carrito(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        self.assertFalse(self.client.session.get('cart'))

    def test_checkout_registra_audit_log(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 123 #45-67',
            'ciudad': 'Bogota',
        })
        pedido = PedidoVenta.objects.first()
        self.assertTrue(
            AuditLog.objects.filter(
                action='pedidos.create', object_id=str(pedido.id_pedido)
            ).exists()
        )


class CheckoutDireccionIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.variante.id_variante): 1}
        session.save()

    def test_checkout_persiste_direccion_en_cliente(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Avenida 12 #33-44',
            'ciudad': 'Bogota',
        })
        direccion = DireccionUsuario.objects.filter(usuario=self.user, es_predeterminada_envio=True).first()
        self.assertIsNotNone(direccion)
        self.assertEqual(direccion.linea1, 'Avenida 12 #33-44')

    def test_checkout_persiste_direccion_en_legacy(self):
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Avenida 12 #33-44',
            'ciudad': 'Bogota',
        })
        direccion = DireccionUsuario.objects.filter(usuario=self.user, es_predeterminada_envio=True).first()
        self.assertIsNotNone(direccion)
        self.assertEqual(direccion.linea1, 'Avenida 12 #33-44')

    def test_checkout_segunda_compra_actualiza_direccion_cliente(self):
        DireccionUsuario.objects.create(
            usuario=self.user,
            tipo_direccion='ENVIO',
            etiqueta='Old',
            nombre_destinatario='Test',
            linea1='Direccion anterior',
            ciudad='Bogota',
            codigo_pais='CO',
            es_predeterminada_envio=True,
        )
        self.client.post(reverse('checkout'), {
            'metodo_pago': 'contraentrega',
            'direccion': 'Calle 20 #10-10',
            'ciudad': 'Bogota',
        })
        direccion = DireccionUsuario.objects.filter(usuario=self.user, es_predeterminada_envio=True).first()
        self.assertEqual(direccion.linea1, 'Calle 20 #10-10')


class LegacyAdminAuditIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.client.force_login(self.admin)
        self.user = make_user('audit.user@test.com')
        self.cliente = make_cliente(self.user)
        self.variante = make_variante(stock=5)
        ensure_salida_movimiento()

    def test_crear_pedido_legacy_registra_audit(self):
        self.client.post(reverse('crear_pedido'), {
            'cliente': self.cliente.pk,
            'variante': self.variante.pk,
            'cantidad': 1,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        })
        self.assertTrue(
            AuditLog.objects.filter(action='pedidos.create').exists()
        )

    def test_crear_pedido_legacy_persiste_en_bd(self):
        self.client.post(reverse('crear_pedido'), {
            'cliente': self.cliente.pk,
            'variante': self.variante.pk,
            'cantidad': 1,
            'direccion_linea1': 'Calle 10 #20-30',
            'ciudad': 'Bogota',
            'estado': 'PENDIENTE_PAGO',
        })
        self.assertTrue(PedidoVenta.objects.filter(cliente=self.cliente).exists())