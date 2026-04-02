from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from core.models import AuditLog
from clientes.models import Cliente
from inventario.models import ProductoMaquillaje
from usuarios.models import Rol
from web.models import Clientes as LegacyClientes
from .models import DetallePedido, Pedido, Pedidos
from .services import create_pedido_from_cart


class CartCheckoutTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.rol, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
		self.user = get_user_model().objects.create_user(
			email='user@test.com', password='Pwd12345!', id_rol=self.rol, nombre1='Test'
		)
		self.producto = ProductoMaquillaje.objects.create(
			nombre='Prod', cantidad=10, estado='disponible', fecha_ingreso='2024-01-01',
			stock=5, precio=Decimal('10000'), descripcion='desc', marca='Marca'
		)

	def _force_login(self):
		self.client.force_login(self.user)

	def test_add_to_cart_success_ajax(self):
		self._force_login()
		url = reverse('carrito_agregar', args=[self.producto.id_inventario])
		resp = self.client.post(url, {'cantidad': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data.get('ok'))
		session_cart = self.client.session.get('cart', {})
		self.assertEqual(session_cart.get(str(self.producto.id_inventario)), 1)

	def test_add_to_cart_insufficient_stock(self):
		self._force_login()
		self.producto.stock = 1
		self.producto.save(update_fields=['stock'])
		url = reverse('carrito_agregar', args=[self.producto.id_inventario])
		resp = self.client.post(url, {'cantidad': 5}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		self.assertEqual(resp.status_code, 400)
		data = resp.json()
		self.assertFalse(data.get('ok'))
		self.assertIn('stock', data.get('error', '').lower())

	def test_add_to_cart_inactive_product_returns_404(self):
		self._force_login()
		self.producto.is_active = False
		self.producto.save(update_fields=['is_active'])
		url = reverse('carrito_agregar', args=[self.producto.id_inventario])
		resp = self.client.post(url, {'cantidad': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		self.assertEqual(resp.status_code, 404)

	def test_checkout_creates_order_and_deducts_stock_and_audit(self):
		self._force_login()
		session = self.client.session
		session['cart'] = {str(self.producto.id_inventario): 2}
		session.save()

		url = reverse('checkout')
		resp = self.client.post(url, {
			'metodo_pago': 'contraentrega',
			'direccion': 'Calle 123 #45-67',
		})

		self.assertEqual(resp.status_code, 302)
		self.assertEqual(Pedido.objects.count(), 1)
		pedido = Pedido.objects.first()
		self.assertEqual(pedido.total, Decimal('20000'))
		self.assertEqual(DetallePedido.objects.count(), 1)
		detalle = DetallePedido.objects.first()
		self.assertEqual(detalle.cantidad, 2)
		self.assertEqual(detalle.producto.id_inventario, self.producto.id_inventario)

		self.producto.refresh_from_db()
		self.assertEqual(self.producto.stock, 3)

		# Cart cleared
		self.assertFalse(self.client.session.get('cart'))
		self.assertTrue(AuditLog.objects.filter(action='pedidos.create', object_id=str(pedido.id)).exists())

	def test_checkout_fails_when_product_inactive(self):
		self._force_login()
		self.producto.is_active = False
		self.producto.save(update_fields=['is_active'])
		session = self.client.session
		session['cart'] = {str(self.producto.id_inventario): 1}
		session.save()

		resp = self.client.post(reverse('checkout'), {
			'metodo_pago': 'contraentrega',
			'direccion': 'Calle 123',
		})
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(Pedido.objects.count(), 0)
		self.assertEqual(resp.url, reverse('carrito'))

	def test_checkout_prefills_address_from_cliente_model(self):
		self._force_login()
		Cliente.objects.create(usuario=self.user, direccion='Calle 55 #10-20')
		session = self.client.session
		session['cart'] = {str(self.producto.id_inventario): 1}
		session.save()

		resp = self.client.get(reverse('checkout'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.context['direccion_prefill'], 'Calle 55 #10-20')

	def test_checkout_prefills_address_from_last_order_when_no_cliente_records(self):
		self._force_login()
		Pedido.objects.create(
			usuario=self.user,
			direccion_envio='Carrera 9 #80-11',
			metodo_pago='contraentrega',
			estado='pendiente',
			total=Decimal('10000'),
		)
		session = self.client.session
		session['cart'] = {str(self.producto.id_inventario): 1}
		session.save()

		resp = self.client.get(reverse('checkout'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.context['direccion_prefill'], 'Carrera 9 #80-11')

	def test_checkout_persists_address_for_future_prefill(self):
		self._force_login()
		session = self.client.session
		session['cart'] = {str(self.producto.id_inventario): 1}
		session.save()

		resp = self.client.post(reverse('checkout'), {
			'metodo_pago': 'contraentrega',
			'direccion': 'Avenida 12 #33-44',
		})

		self.assertEqual(resp.status_code, 302)
		cliente = Cliente.objects.filter(usuario=self.user).first()
		legacy = LegacyClientes.objects.filter(correo__iexact=self.user.email).first()
		self.assertIsNotNone(cliente)
		self.assertEqual(cliente.direccion, 'Avenida 12 #33-44')
		self.assertIsNotNone(legacy)
		self.assertEqual(legacy.direccion, 'Avenida 12 #33-44')


class PedidoServiceTests(TestCase):
	def setUp(self):
		self.rol, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
		self.user = get_user_model().objects.create_user(
			email='svc@test.com', password='Pwd12345!', id_rol=self.rol, nombre1='Svc'
		)
		self.producto = ProductoMaquillaje.objects.create(
			nombre='Prod SVC', cantidad=10, estado='disponible', fecha_ingreso='2024-01-01',
			stock=2, precio=Decimal('5000'), descripcion='desc', marca='Marca'
		)

	def test_service_validates_stock(self):
		items = [{'producto': self.producto, 'cantidad': 5}]
		with self.assertRaises(ValidationError):
			create_pedido_from_cart(self.user, items, 'Dir', 'contraentrega')

	def test_service_creates_audit(self):
		items = [{'producto': self.producto, 'cantidad': 1}]
		pedido = create_pedido_from_cart(self.user, items, 'Dir', 'contraentrega')
		self.assertTrue(AuditLog.objects.filter(action='pedidos.create', object_id=str(pedido.id)).exists())


class LegacyPedidosAdminTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.rol_admin, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
		self.rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
		self.admin = get_user_model().objects.create_user(
			email='admin@test.com', password='Pwd12345!', id_rol=self.rol_admin, nombre1='Admin', is_superuser=True
		)
		self.user = get_user_model().objects.create_user(
			email='user2@test.com', password='Pwd12345!', id_rol=self.rol_cliente, nombre1='User'
		)
		self.pedido = Pedidos.objects.create(
			usuario='U', telefono='1234567890', producto='Prod', precio=Decimal('1000'),
			direccion='Dir', cantidad=1, fecha='2024-01-01'
		)

	def test_non_admin_redirected(self):
		self.client.force_login(self.user)
		resp = self.client.get(reverse('lista_pedidos'))
		self.assertEqual(resp.status_code, 302)
		self.assertIn('/login/', resp.url)

	def test_admin_can_access_and_creates_audit_on_create(self):
		self.client.force_login(self.admin)
		resp = self.client.get(reverse('lista_pedidos'))
		self.assertEqual(resp.status_code, 200)

		create_resp = self.client.post(reverse('crear_pedido'), {
			'usuario': 'Nuevo',
			'telefono': '1234567890',
			'producto': 'Prod2',
			'precio': 2000,
			'direccion': 'Dir',
			'cantidad': 1,
			'fecha': '2026-04-10',
		})
		self.assertEqual(create_resp.status_code, 302)
		self.assertTrue(AuditLog.objects.filter(action='pedidos.legacy.create').exists())
