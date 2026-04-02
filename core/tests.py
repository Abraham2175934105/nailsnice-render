from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from usuarios.models import Rol


class ProfilePasswordTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.rol = Rol.objects.create(nombre=Rol.CLIENTE)
		self.user = get_user_model().objects.create_user(
			email='user@test.com', password='Pwd12345!', id_rol=self.rol, nombre1='Test'
		)
		self.client.force_login(self.user)

	def test_change_password_happy_path(self):
		url = reverse('perfil')
		resp = self.client.post(url, {
			'action': 'change_password',
			'actual': 'Pwd12345!',
			'nueva': 'NuevaPass1!',
			'confirmar': 'NuevaPass1!'
		})
		# Redirects back to perfil on success
		self.assertEqual(resp.status_code, 302)
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('NuevaPass1!'))

	def test_change_password_rejects_weak(self):
		url = reverse('perfil')
		resp = self.client.post(url, {
			'action': 'change_password',
			'actual': 'Pwd12345!',
			'nueva': 'weakpass',
			'confirmar': 'weakpass'
		})
		# Re-render with errors (status 200)
		self.assertEqual(resp.status_code, 200)
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('Pwd12345!'))
