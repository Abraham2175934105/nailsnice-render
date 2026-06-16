from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from clientes.models import Cliente
from usuarios.models import Empleado, RolAcceso, UsuarioRol
from .models import Agendamiento, CategoriaServicio, Servicio, TipoServicio


class UnauthenticatedAccessTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', nombre='Empleado')
        self.rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', nombre='Cliente')

        self.employee_user = get_user_model().objects.create_user(
            correo='emp.unauth@test.com', password='Pwd12345!', nombre='Emp',
        )
        UsuarioRol.objects.create(usuario=self.employee_user, rol=self.rol_empleado)
        self.employee = Empleado.objects.create(usuario=self.employee_user, codigo_empleado='EMP-U01')

        self.cliente_user = get_user_model().objects.create_user(
            correo='cli.unauth@test.com', password='Pwd12345!', nombre='Cli',
        )
        UsuarioRol.objects.create(usuario=self.cliente_user, rol=self.rol_cliente)
        self.cliente = Cliente.objects.create(usuario=self.cliente_user)

        self.tipo = TipoServicio.objects.create(codigo='UNAUTH', nombre='Unauth')
        self.categoria = CategoriaServicio.objects.create(nombre='Gen', descripcion='General')
        self.servicio = Servicio.objects.create(
            nombre='Servicio unauth', descripcion='', precio_base='10000',
            duracion_minutos=30, categoria_servicio=self.categoria,
            activo=True, tipo_servicio=self.tipo,
        )
        next_day = date.today() + timedelta(days=1)
        start = datetime.combine(next_day, time(9, 0))
        self.agendamiento = Agendamiento.objects.create(
            cliente=self.cliente, servicio=self.servicio, empleado=self.employee,
            estado='PENDIENTE', inicia_en=start, termina_en=start + timedelta(minutes=30),
        )

    def test_list_redirects_unauthenticated(self):
        resp = self.client.get(reverse('empleado_agendamientos'))
        self.assertIn(resp.status_code, [302, 403])

    def test_create_redirects_unauthenticated(self):
        resp = self.client.get(reverse('empleado_crear_agendamiento'))
        self.assertIn(resp.status_code, [302, 403])

    def test_edit_redirects_unauthenticated(self):
        resp = self.client.get(
            reverse('empleado_editar_agendamiento', args=[self.agendamiento.pk])
        )
        self.assertIn(resp.status_code, [302, 403])


class ClienteRoleAccessTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', nombre='Empleado')
        self.rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', nombre='Cliente')

        self.employee_user = get_user_model().objects.create_user(
            correo='emp.role@test.com', password='Pwd12345!', nombre='Emp',
        )
        UsuarioRol.objects.create(usuario=self.employee_user, rol=self.rol_empleado)
        self.employee = Empleado.objects.create(usuario=self.employee_user, codigo_empleado='EMP-R01')

        self.cliente_user = get_user_model().objects.create_user(
            correo='cli.role@test.com', password='Pwd12345!', nombre='Cli',
        )
        UsuarioRol.objects.create(usuario=self.cliente_user, rol=self.rol_cliente)
        self.cliente = Cliente.objects.create(usuario=self.cliente_user)

        self.tipo = TipoServicio.objects.create(codigo='ROLE', nombre='Role')
        self.categoria = CategoriaServicio.objects.create(nombre='RoleCat', descripcion='')
        self.servicio = Servicio.objects.create(
            nombre='Servicio role', descripcion='', precio_base='20000',
            duracion_minutos=30, categoria_servicio=self.categoria,
            activo=True, tipo_servicio=self.tipo,
        )
        next_day = date.today() + timedelta(days=1)
        start = datetime.combine(next_day, time(10, 0))
        self.agendamiento = Agendamiento.objects.create(
            cliente=self.cliente, servicio=self.servicio, empleado=self.employee,
            estado='PENDIENTE', inicia_en=start, termina_en=start + timedelta(minutes=30),
        )

    def test_cliente_cannot_access_employee_list(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.get(reverse('empleado_agendamientos'))
        self.assertIn(resp.status_code, [302, 403])

    def test_cliente_cannot_access_employee_create(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.get(reverse('empleado_crear_agendamiento'))
        self.assertIn(resp.status_code, [302, 403])

    def test_cliente_cannot_access_employee_edit(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.get(
            reverse('empleado_editar_agendamiento', args=[self.agendamiento.pk])
        )
        self.assertIn(resp.status_code, [302, 403])


class EmployeeEditAgendamientoTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', nombre='Empleado')
        self.rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', nombre='Cliente')

        self.employee_user = get_user_model().objects.create_user(
            correo='emp.edit@test.com', password='Pwd12345!', nombre='Emp',
        )
        UsuarioRol.objects.create(usuario=self.employee_user, rol=self.rol_empleado)
        self.employee = Empleado.objects.create(usuario=self.employee_user, codigo_empleado='EMP-E01')

        self.cliente_user = get_user_model().objects.create_user(
            correo='cli.edit@test.com', password='Pwd12345!', nombre='Cli',
        )
        UsuarioRol.objects.create(usuario=self.cliente_user, rol=self.rol_cliente)
        self.cliente = Cliente.objects.create(usuario=self.cliente_user)

        self.tipo = TipoServicio.objects.create(codigo='EDIT', nombre='Edit')
        self.categoria = CategoriaServicio.objects.create(nombre='EditCat', descripcion='')
        self.servicio = Servicio.objects.create(
            nombre='Servicio editable', descripcion='', precio_base='30000',
            duracion_minutos=60, categoria_servicio=self.categoria,
            activo=True, tipo_servicio=self.tipo,
        )
        next_day = date.today() + timedelta(days=1)
        self.start = datetime.combine(next_day, time(14, 0))
        self.agendamiento = Agendamiento.objects.create(
            cliente=self.cliente, servicio=self.servicio, empleado=self.employee,
            estado='PENDIENTE', inicia_en=self.start,
            termina_en=self.start + timedelta(minutes=60),
        )

    def test_employee_can_view_own_edit_form(self):
        self.client.force_login(self.employee_user)
        resp = self.client.get(
            reverse('empleado_editar_agendamiento', args=[self.agendamiento.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_employee_edit_own_agendamiento_success(self):
        self.client.force_login(self.employee_user)
        new_start = self.start + timedelta(hours=2)
        payload = {
            'cliente': self.cliente.pk,
            'servicio': self.servicio.pk,
            'inicia_en': new_start.strftime('%Y-%m-%dT%H:%M'),
            'termina_en': (new_start + timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M'),
            'estado': 'CONFIRMADO',
            'canal': 'WEB',
            'notas': 'Actualizado',
        }
        resp = self.client.post(
            reverse('empleado_editar_agendamiento', args=[self.agendamiento.pk]), payload
        )
        self.assertEqual(resp.status_code, 302)
        self.agendamiento.refresh_from_db()
        self.assertEqual(self.agendamiento.estado, 'CONFIRMADO')

    def test_employee_edit_does_not_change_assigned_employee(self):
        self.client.force_login(self.employee_user)
        new_start = self.start + timedelta(hours=3)
        payload = {
            'cliente': self.cliente.pk,
            'servicio': self.servicio.pk,
            'inicia_en': new_start.strftime('%Y-%m-%dT%H:%M'),
            'termina_en': (new_start + timedelta(minutes=60)).strftime('%Y-%m-%dT%H:%M'),
            'estado': 'PENDIENTE',
            'canal': 'WEB',
            'notas': '',
        }
        self.client.post(
            reverse('empleado_editar_agendamiento', args=[self.agendamiento.pk]), payload
        )
        self.agendamiento.refresh_from_db()
        self.assertEqual(self.agendamiento.empleado_id, self.employee.pk)


class AgendamientoEstadoTransitionTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', nombre='Empleado')
        self.rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', nombre='Cliente')

        self.employee_user = get_user_model().objects.create_user(
            correo='emp.estado@test.com', password='Pwd12345!', nombre='Emp',
        )
        UsuarioRol.objects.create(usuario=self.employee_user, rol=self.rol_empleado)
        self.employee = Empleado.objects.create(usuario=self.employee_user, codigo_empleado='EMP-EST')

        self.cliente_user = get_user_model().objects.create_user(
            correo='cli.estado@test.com', password='Pwd12345!', nombre='Cli',
        )
        UsuarioRol.objects.create(usuario=self.cliente_user, rol=self.rol_cliente)
        self.cliente = Cliente.objects.create(usuario=self.cliente_user)

        self.tipo = TipoServicio.objects.create(codigo='EST', nombre='Estado')
        self.categoria = CategoriaServicio.objects.create(nombre='EstadoCat', descripcion='')
        self.servicio = Servicio.objects.create(
            nombre='Servicio estado', descripcion='', precio_base='40000',
            duracion_minutos=60, categoria_servicio=self.categoria,
            activo=True, tipo_servicio=self.tipo,
        )
        next_day = date.today() + timedelta(days=1)
        self.start = datetime.combine(next_day, time(8, 0))

    def _crear_agendamiento(self, estado='PENDIENTE'):
        return Agendamiento.objects.create(
            cliente=self.cliente, servicio=self.servicio, empleado=self.employee,
            estado=estado, inicia_en=self.start,
            termina_en=self.start + timedelta(minutes=60),
        )

    def _payload(self, agendamiento, estado):
        return {
            'cliente': self.cliente.pk,
            'servicio': self.servicio.pk,
            'inicia_en': agendamiento.inicia_en.strftime('%Y-%m-%dT%H:%M'),
            'termina_en': agendamiento.termina_en.strftime('%Y-%m-%dT%H:%M'),
            'estado': estado,
            'canal': 'WEB',
            'notas': '',
        }

    def test_pendiente_to_confirmado(self):
        ag = self._crear_agendamiento('PENDIENTE')
        self.client.force_login(self.employee_user)
        resp = self.client.post(
            reverse('empleado_editar_agendamiento', args=[ag.pk]),
            self._payload(ag, 'CONFIRMADO'),
        )
        self.assertEqual(resp.status_code, 302)
        ag.refresh_from_db()
        self.assertEqual(ag.estado, 'CONFIRMADO')

    def test_pendiente_to_cancelado(self):
        ag = self._crear_agendamiento('PENDIENTE')
        self.client.force_login(self.employee_user)
        resp = self.client.post(
            reverse('empleado_editar_agendamiento', args=[ag.pk]),
            self._payload(ag, 'CANCELADO'),
        )
        self.assertEqual(resp.status_code, 302)
        ag.refresh_from_db()
        self.assertEqual(ag.estado, 'CANCELADO')


class EmployeeAgendamientoFormValidationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol_empleado, _ = RolAcceso.objects.get_or_create(codigo='EMPLEADO', nombre='Empleado')
        self.rol_cliente, _ = RolAcceso.objects.get_or_create(codigo='CLIENTE', nombre='Cliente')

        self.employee_user = get_user_model().objects.create_user(
            correo='emp.form@test.com', password='Pwd12345!', nombre='Emp',
        )
        UsuarioRol.objects.create(usuario=self.employee_user, rol=self.rol_empleado)
        self.employee = Empleado.objects.create(usuario=self.employee_user, codigo_empleado='EMP-FORM')

        self.cliente_user = get_user_model().objects.create_user(
            correo='cli.form@test.com', password='Pwd12345!', nombre='Cli',
        )
        UsuarioRol.objects.create(usuario=self.cliente_user, rol=self.rol_cliente)
        self.cliente = Cliente.objects.create(usuario=self.cliente_user)

        self.tipo = TipoServicio.objects.create(codigo='FORM', nombre='Form')
        self.categoria = CategoriaServicio.objects.create(nombre='FormCat', descripcion='')
        self.servicio = Servicio.objects.create(
            nombre='Servicio form', descripcion='', precio_base='25000',
            duracion_minutos=60, categoria_servicio=self.categoria,
            activo=True, tipo_servicio=self.tipo,
        )

    def test_create_without_required_fields_returns_form_errors(self):
        self.client.force_login(self.employee_user)
        resp = self.client.post(reverse('empleado_crear_agendamiento'), {})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Agendamiento.objects.exists())

    def test_create_end_before_start_shows_error(self):
        self.client.force_login(self.employee_user)
        start_time = datetime.combine(date.today() + timedelta(days=1), time(10, 0))
        payload = {
            'cliente': self.cliente.pk,
            'servicio': self.servicio.pk,
            'inicia_en': start_time.strftime('%Y-%m-%dT%H:%M'),
            'termina_en': (start_time - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
            'estado': 'PENDIENTE',
            'canal': 'WEB',
            'notas': '',
        }
        resp = self.client.post(reverse('empleado_crear_agendamiento'), payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Agendamiento.objects.exists())

    def test_create_end_equals_start_shows_error(self):
        self.client.force_login(self.employee_user)
        start_time = datetime.combine(date.today() + timedelta(days=1), time(11, 0))
        payload = {
            'cliente': self.cliente.pk,
            'servicio': self.servicio.pk,
            'inicia_en': start_time.strftime('%Y-%m-%dT%H:%M'),
            'termina_en': start_time.strftime('%Y-%m-%dT%H:%M'),
            'estado': 'PENDIENTE',
            'canal': 'WEB',
            'notas': '',
        }
        resp = self.client.post(reverse('empleado_crear_agendamiento'), payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Agendamiento.objects.exists())