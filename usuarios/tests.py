from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
from usuarios.models import Rol


class AdminPermissionsTests(TestCase):
	def setUp(self):
		self.api_client = APIClient()
		self.rol_admin, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
		self.rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
		self.admin = get_user_model().objects.create_user(
			email='admin@test.com', password='Pwd12345!', id_rol=self.rol_admin, nombre1='Admin', is_superuser=True
		)
		self.user = get_user_model().objects.create_user(
			email='user@test.com', password='Pwd12345!', id_rol=self.rol_cliente, nombre1='User'
		)

	def test_productos_read_allowed_for_client(self):
		self.api_client.force_authenticate(user=self.user)
		resp = self.api_client.get('/api/productos/')
		self.assertEqual(resp.status_code, 200)

	def test_productos_write_not_allowed(self):
		self.api_client.force_authenticate(user=self.user)
		resp = self.api_client.post('/api/productos/', {
			'nombre': 'Prod',
			'descripcion': 'Descripcion valida',
			'precio': Decimal('10.00'),
		}, format='json')
		self.assertEqual(resp.status_code, 405)

	def test_productos_write_not_allowed_for_admin(self):
		self.api_client.force_authenticate(user=self.admin)
		resp = self.api_client.post('/api/productos/', {
			'nombre': 'Prod Admin',
			'descripcion': 'Descripcion suficientemente larga',
			'precio': Decimal('10.00'),
		}, format='json')
		self.assertEqual(resp.status_code, 405)

	def test_usuarios_endpoint_is_admin_only(self):
		self.api_client.force_authenticate(user=self.user)
		resp = self.api_client.get('/api/usuarios/')
		self.assertEqual(resp.status_code, 403)

		self.api_client.force_authenticate(user=self.admin)
		resp_admin = self.api_client.get('/api/usuarios/')
		self.assertEqual(resp_admin.status_code, 200)
