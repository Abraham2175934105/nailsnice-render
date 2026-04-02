from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from productos.models import Producto
from servicios.models import Servicio, TipoServicio
from usuarios.models import Rol, Usuario

from .models import Cliente, ServicioCliente


class ClienteValidationsTest(TestCase):
    def setUp(self):
        self.rol = Rol.objects.create(nombre='Cliente', descripcion='Cliente')
        self.usuario = Usuario.objects.create_user(
            email='cliente@test.com',
            password='Test12345!',
            nombre1='Cliente',
            apellido1='Prueba',
            estado_usuario='Activo',
            id_rol=self.rol,
        )

    def test_cliente_no_acepta_puntos_negativos(self):
        cliente = Cliente(usuario=self.usuario, puntos_fidelidad=-1)
        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_servicio_cliente_no_acepta_cupones_ni_promociones_negativas(self):
        cliente = Cliente.objects.create(usuario=self.usuario, puntos_fidelidad=0)
        servicio_cliente = ServicioCliente(
            cliente=cliente,
            canal_comunicacion='Email',
            control_agendamiento='Pendiente',
            estado_ticket='Abierto',
            cupones=-1,
            promociones=-2,
        )
        with self.assertRaises(ValidationError):
            servicio_cliente.full_clean()


class CrossAppValidationsTest(TestCase):
    def test_producto_exige_descripcion_minima(self):
        producto = Producto(
            nombre='Producto demo',
            descripcion='corta',
            precio=Decimal('10.00'),
        )
        with self.assertRaises(ValidationError):
            producto.full_clean()

    def test_servicio_no_acepta_duracion_estimada_negativa(self):
        tipo = TipoServicio.objects.create(nombre_tipo='Manicura')
        servicio = Servicio(
            nombre_servicio='Manicura demo',
            categoria_servicio='Manos',
            precio_servicio=Decimal('20.00'),
            duracion_servicio='45m',
            duracion_estimada=-15,
            tipo_servicio=tipo,
        )
        with self.assertRaises(ValidationError):
            servicio.full_clean()
