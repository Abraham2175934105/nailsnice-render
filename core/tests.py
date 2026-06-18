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


from core.forms import RegistroForm

class RegistroFormValidationTests(TestCase):
    def setUp(self):
        from usuarios.models import Rol
        self.rol_cliente, _ = Rol.objects.get_or_create(
            nombre=Rol.CLIENTE,
            defaults={'descripcion': 'Cliente', 'es_sistema': True}
        )

    def test_valid_form_data(self):
        data = {
            'nombre': 'Carlos',
            'apellido': 'Gomez',
            'telefono': '3123456789',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'carlos.gomez@test.com',
            'contrasena': 'Segura123!'
        }
        form = RegistroForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_name_multiple_words(self):
        data = {
            'nombre': 'Carlos Alberto',
            'apellido': 'Gomez',
            'telefono': '3123456789',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'carlos.gomez@test.com',
            'contrasena': 'Segura123!'
        }
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_invalid_surname_special_chars(self):
        data = {
            'nombre': 'Carlos',
            'apellido': 'Gomez123',
            'telefono': '3123456789',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'carlos.gomez@test.com',
            'contrasena': 'Segura123!'
        }
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('apellido', form.errors)

    def test_unique_email_and_phone(self):
        get_user_model().objects.create_user(
            email='carlos.gomez@test.com',
            password='Password123!',
            nombre1='Carlos',
            apellido1='Gomez',
            telefono='3123456789'
        )
        
        # Test repeat email
        data_repeat_email = {
            'nombre': 'Maria',
            'apellido': 'Perez',
            'telefono': '3129999999',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'Carlos.Gomez@test.com',
            'contrasena': 'Segura123!'
        }
        form = RegistroForm(data=data_repeat_email)
        self.assertFalse(form.is_valid())
        self.assertIn('correo', form.errors)
        self.assertEqual(form.errors['correo'][0], 'El correo ya está registrado.')

        # Test repeat phone
        data_repeat_phone = {
            'nombre': 'Maria',
            'apellido': 'Perez',
            'telefono': '3123456789',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'maria.perez@test.com',
            'contrasena': 'Segura123!'
        }
        form = RegistroForm(data=data_repeat_phone)
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)
        self.assertEqual(form.errors['telefono'][0], 'Este teléfono ya está registrado.')

    def test_password_strength_validations(self):
        base_data = {
            'nombre': 'Carlos',
            'apellido': 'Gomez',
            'telefono': '3123456789',
            'linea1': 'Calle 45 #12-34',
            'ciudad': 'Bogotá',
            'departamento': 'Cundinamarca',
            'correo': 'carlos.gomez@test.com',
        }
        
        # Short password
        data = base_data.copy()
        data['contrasena'] = 'Seg1!'
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contrasena', form.errors)

        # No uppercase
        data['contrasena'] = 'segura123!'
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contrasena', form.errors)

        # No lowercase
        data['contrasena'] = 'SEGURA123!'
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contrasena', form.errors)

        # No number
        data['contrasena'] = 'Segurall!'
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contrasena', form.errors)

        # No special character
        data['contrasena'] = 'Segura1234'
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('contrasena', form.errors)
