from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from clientes.models import Cliente
from usuarios.models import Empleado, Rol
from .models import Agendamiento, Servicio, TipoServicio


class EmployeeAgendamientosTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.rol_empleado, _ = Rol.objects.get_or_create(nombre=Rol.EMPLEADO)
		self.rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)

		self.employee_user = get_user_model().objects.create_user(
			email='empleado.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_empleado,
			nombre1='Empleado',
		)
		self.other_employee_user = get_user_model().objects.create_user(
			email='otro.empleado.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_empleado,
			nombre1='Otro',
		)
		self.employee = Empleado.objects.create(usuario=self.employee_user)
		self.other_employee = Empleado.objects.create(usuario=self.other_employee_user)

		self.cliente_user = get_user_model().objects.create_user(
			email='cliente.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_cliente,
			nombre1='Cliente',
		)
		self.other_cliente_user = get_user_model().objects.create_user(
			email='cliente2.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_cliente,
			nombre1='Cliente2',
		)
		self.cliente = Cliente.objects.create(usuario=self.cliente_user, direccion='Calle 1 #2-3')
		self.other_cliente = Cliente.objects.create(usuario=self.other_cliente_user, direccion='Carrera 4 #5-6')

		self.tipo = TipoServicio.objects.create(nombre_tipo='Manicura')
		self.servicio = Servicio.objects.create(
			nombre_servicio='Manicura tradicional',
			descripcion='Servicio base',
			precio_servicio='45000',
			duracion_servicio='1h',
			categoria_servicio='Uñas',
			estado_servicio='Activo',
			tipo_servicio=self.tipo,
		)

		next_day = date.today() + timedelta(days=1)
		self.my_agendamiento = Agendamiento.objects.create(
			cliente=self.cliente,
			servicio=self.servicio,
			empleado=self.employee,
			fecha_agendamiento=next_day,
			hora_agendamiento='09:00',
			estado_agendamiento='Pendiente',
		)
		self.other_agendamiento = Agendamiento.objects.create(
			cliente=self.other_cliente,
			servicio=self.servicio,
			empleado=self.other_employee,
			fecha_agendamiento=next_day,
			hora_agendamiento='10:00',
			estado_agendamiento='Pendiente',
		)

	def test_employee_list_only_shows_own_agendamientos(self):
		self.client.force_login(self.employee_user)
		resp = self.client.get(reverse('empleado_agendamientos'))

		self.assertEqual(resp.status_code, 200)
		listed_ids = [a.id for a in resp.context['agendamientos']]
		self.assertIn(self.my_agendamiento.id, listed_ids)
		self.assertNotIn(self.other_agendamiento.id, listed_ids)

	def test_employee_cannot_edit_other_employee_agendamiento(self):
		self.client.force_login(self.employee_user)
		resp = self.client.get(reverse('empleado_editar_agendamiento', args=[self.other_agendamiento.id]))
		self.assertEqual(resp.status_code, 404)

	def test_employee_create_agendamiento_assigns_logged_employee(self):
		self.client.force_login(self.employee_user)
		payload = {
			'cliente': self.cliente.id,
			'servicio': self.servicio.id,
			'fecha_agendamiento': (date.today() + timedelta(days=2)).isoformat(),
			'hora_agendamiento': '11:00',
			'estado_agendamiento': 'Confirmado',
			'notas': 'Cliente preferente',
		}

		resp = self.client.post(reverse('empleado_crear_agendamiento'), payload)

		self.assertEqual(resp.status_code, 302)
		nuevo = Agendamiento.objects.order_by('-id').first()
		self.assertEqual(nuevo.empleado_id, self.employee.id)


class EmployeeAgendamientosValidationTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.rol_empleado, _ = Rol.objects.get_or_create(nombre=Rol.EMPLEADO)
		self.rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)

		self.employee_user = get_user_model().objects.create_user(
			email='empleado.val.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_empleado,
			nombre1='Empleado',
		)
		self.employee = Empleado.objects.create(usuario=self.employee_user)

		self.cliente_user = get_user_model().objects.create_user(
			email='cliente.val.agenda@test.com',
			password='Pwd12345!',
			id_rol=self.rol_cliente,
			nombre1='Cliente',
		)
		self.cliente = Cliente.objects.create(usuario=self.cliente_user, direccion='Calle 8 #19-20')

		self.tipo = TipoServicio.objects.create(nombre_tipo='Pedicura')
		self.servicio = Servicio.objects.create(
			nombre_servicio='Pedicura spa',
			descripcion='Servicio completo',
			precio_servicio='55000',
			duracion_servicio='1h',
			categoria_servicio='Pies',
			estado_servicio='Activo',
			tipo_servicio=self.tipo,
		)

	def test_employee_create_agendamiento_past_date_shows_alerts(self):
		self.client.force_login(self.employee_user)
		payload = {
			'cliente': self.cliente.id,
			'servicio': self.servicio.id,
			'fecha_agendamiento': (date.today() - timedelta(days=1)).isoformat(),
			'hora_agendamiento': '11:00',
			'estado_agendamiento': 'Pendiente',
			'notas': 'Prueba',
		}

		resp = self.client.post(reverse('empleado_crear_agendamiento'), payload)

		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'La fecha no puede ser anterior a hoy')
		self.assertContains(resp, 'Revisa los campos antes de guardar')
		self.assertContains(resp, 'Corrige los errores del formulario para guardar el agendamiento')

	def test_employee_create_agendamiento_duplicate_slot_shows_errors(self):
		self.client.force_login(self.employee_user)
		target_date = date.today() + timedelta(days=2)
		Agendamiento.objects.create(
			cliente=self.cliente,
			servicio=self.servicio,
			empleado=self.employee,
			fecha_agendamiento=target_date,
			hora_agendamiento='09:30',
			estado_agendamiento='Pendiente',
		)

		payload = {
			'cliente': self.cliente.id,
			'servicio': self.servicio.id,
			'fecha_agendamiento': target_date.isoformat(),
			'hora_agendamiento': '09:30',
			'estado_agendamiento': 'Confirmado',
			'notas': '',
		}

		resp = self.client.post(reverse('empleado_crear_agendamiento'), payload)

		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Ya tienes un agendamiento en esa fecha y hora')
		self.assertContains(resp, 'Revisa los campos antes de guardar')
