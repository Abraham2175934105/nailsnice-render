from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import AuditLog
from usuarios.models import Rol
from .forms import ProductoMaquillajeForm
from .models import ProductoMaquillaje


class InventarioAdminTests(TestCase):
	def setUp(self):
		self.rol_admin, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
		self.rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
		self.admin = get_user_model().objects.create_user(
			email='admin@test.com', password='Pwd12345!', id_rol=self.rol_admin, nombre1='Admin', is_superuser=True
		)
		self.cliente = get_user_model().objects.create_user(
			email='cliente@test.com', password='Pwd12345!', id_rol=self.rol_cliente, nombre1='Cliente'
		)
		self.producto_activo = ProductoMaquillaje.objects.create(
			nombre='Prod A', cantidad=10, estado='disponible', fecha_ingreso='2024-01-01',
			stock=5, precio='10000', descripcion='desc', marca='Marca'
		)
		self.producto_inactivo = ProductoMaquillaje.objects.create(
			nombre='Prod B', cantidad=10, estado='disponible', fecha_ingreso='2024-01-01',
			stock=5, precio='20000', descripcion='desc', marca='Marca', is_active=False
		)

	def test_non_admin_redirected_from_inventory(self):
		self.client.force_login(self.cliente)
		response = self.client.get(reverse('lista_inventario'))
		self.assertEqual(response.status_code, 302)
		self.assertIn('/login/', response.url)

	def test_admin_sees_only_active_products(self):
		self.client.force_login(self.admin)
		response = self.client.get(reverse('lista_inventario'))
		self.assertEqual(response.status_code, 200)
		productos = list(response.context['productos'])
		self.assertEqual(len(productos), 1)
		self.assertEqual(productos[0].id_inventario, self.producto_activo.id_inventario)

	def test_soft_delete_marks_inactive_and_logs(self):
		self.client.force_login(self.admin)
		response = self.client.get(reverse('eliminar_producto', args=[self.producto_activo.id_inventario]))
		self.assertEqual(response.status_code, 302)
		self.producto_activo.refresh_from_db()
		self.assertFalse(self.producto_activo.is_active)
		self.assertFalse(ProductoMaquillaje.activos.filter(id_inventario=self.producto_activo.id_inventario).exists())
		self.assertTrue(AuditLog.objects.filter(action='inventario.soft_delete', object_id=str(self.producto_activo.id_inventario)).exists())

	def test_inactive_product_cannot_be_edited(self):
		self.client.force_login(self.admin)
		response = self.client.get(reverse('editar_producto', args=[self.producto_inactivo.id_inventario]))
		self.assertEqual(response.status_code, 404)

	def test_edit_product_with_image_does_not_break_audit(self):
		self.client.force_login(self.admin)
		img_bytes = (
			b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
			b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
		)
		img = SimpleUploadedFile('edit.gif', img_bytes, content_type='image/gif')
		response = self.client.post(reverse('editar_producto', args=[self.producto_activo.id_inventario]), {
			'nombre': 'Prod A Editado',
			'cantidad': 10,
			'estado': 'disponible',
			'fecha_ingreso': '2024-01-01',
			'stock': 5,
			'precio': '10000',
			'descripcion': 'descripcion valida',
			'marca': 'Marca',
			'proveedor': 'Proveedor',
			'imagen': img,
		})
		self.assertEqual(response.status_code, 302)
		self.producto_activo.refresh_from_db()
		self.assertTrue(bool(self.producto_activo.imagen))
		self.assertTrue(AuditLog.objects.filter(action='inventario.update').exists())


class InventarioFormTests(TestCase):
	def _base_payload(self):
		return {
			'nombre': 'Producto Test',
			'cantidad': 10,
			'estado': 'disponible',
			'fecha_ingreso': timezone.now().date().isoformat(),
			'stock': 5,
			'precio': '12000',
			'descripcion': 'Descripcion valida',
			'marca': 'MarcaTest',
			'proveedor': 'ProveedorTest',
		}

	def test_clean_fecha_ingreso_valid_date_no_crash(self):
		form = ProductoMaquillajeForm(data=self._base_payload())
		self.assertTrue(form.is_valid(), form.errors)

	def test_clean_fecha_ingreso_future_date_invalid(self):
		data = self._base_payload()
		data['fecha_ingreso'] = (timezone.now().date() + timedelta(days=1)).isoformat()
		form = ProductoMaquillajeForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertIn('fecha_ingreso', form.errors)
