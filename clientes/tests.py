from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APIClient, force_authenticate
from rest_framework import status

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly
from rest_framework.viewsets import ModelViewSet

from clientes.models import (
    Cliente, DireccionUsuario, MetodoPagoCliente,
    CuentaFidelizacion, LibroPuntos,
    TipoMetodoPago, ProveedorPago,
)
from clientes.serializers import (
    ClienteSerializer, DireccionUsuarioSerializer,
    MetodoPagoClienteSerializer, CuentaFidelizacionSerializer,
)
from clientes.views import ClienteViewSet, DireccionUsuarioViewSet

User = get_user_model()


def make_admin():
    return User.objects.create_superuser(
        correo='admin@test.com',
        password='pass1234',
    )

def make_user(correo='user@test.com'):
    return User.objects.create_user(
        correo=correo,
        password='pass1234',
        is_staff=False,
    )

def make_cliente(correo='cliente@test.com'):
    user = make_user(correo=correo)
    return Cliente.objects.create(usuario=user)

def make_direccion(cliente, tipo='ENVIO', predeterminada_envio=False):
    return DireccionUsuario.objects.create(
        usuario=cliente.usuario,
        tipo_direccion=tipo,
        nombre_destinatario='Test Destinatario',
        linea1='Calle 123 # 45-67',
        ciudad='Bogotá',
        codigo_pais='CO',
        es_predeterminada_envio=predeterminada_envio,
    )

def make_cuenta_fidelizacion(cliente, puntos=100):
    return CuentaFidelizacion.objects.create(
        cliente=cliente,
        puntos_actuales=puntos,
        total_ganados=puntos,
        total_redimidos=0,
    )


class ClienteViewSetUnitTest(TestCase):

    def test_queryset_apunta_a_cliente(self):
        self.assertEqual(ClienteViewSet.queryset.model, Cliente)

    def test_serializer_correcto(self):
        self.assertEqual(ClienteViewSet.serializer_class, ClienteSerializer)

    def test_audit_prefix_correcto(self):
        self.assertEqual(ClienteViewSet.audit_prefix, 'clientes.cliente')

    def test_hereda_model_viewset(self):
        self.assertTrue(issubclass(ClienteViewSet, ModelViewSet))

    def test_hereda_audit_mixin(self):
        self.assertTrue(issubclass(ClienteViewSet, AuditViewSetMixin))

    def test_permission_es_admin_only(self):
        self.assertIn(IsAdminOnly, ClienteViewSet.permission_classes)

    def test_select_related_en_queryset(self):
        self.assertIn('usuario', ClienteViewSet.queryset.query.select_related)


class DireccionUsuarioModelUnitTest(TestCase):

    def test_tipo_choices_contiene_envio(self):
        valores = [c[0] for c in DireccionUsuario.TIPO_CHOICES]
        self.assertIn('ENVIO', valores)

    def test_tipo_choices_contiene_factura(self):
        valores = [c[0] for c in DireccionUsuario.TIPO_CHOICES]
        self.assertIn('FACTURA', valores)

    def test_tipo_choices_contiene_otra(self):
        valores = [c[0] for c in DireccionUsuario.TIPO_CHOICES]
        self.assertIn('OTRA', valores)

    def test_codigo_pais_default_es_CO(self):
        field = DireccionUsuario._meta.get_field('codigo_pais')
        self.assertEqual(field.default, 'CO')

    def test_campos_generated_always_no_editables(self):
        self.assertFalse(
            DireccionUsuario._meta.get_field('id_usuario_envio_predeterminado').editable
        )
        self.assertFalse(
            DireccionUsuario._meta.get_field('id_usuario_factura_predeterminado').editable
        )


class MetodoPagoClienteModelUnitTest(TestCase):

    def test_estado_choices_correctos(self):
        valores = [c[0] for c in MetodoPagoCliente.ESTADO_CHOICES]
        self.assertEqual(set(valores), {'ACTIVO', 'INACTIVO', 'REVOCADO'})

    def test_estado_default_es_activo(self):
        field = MetodoPagoCliente._meta.get_field('estado')
        self.assertEqual(field.default, 'ACTIVO')

    def test_campo_token_no_editable_via_serializador(self):
        fields = MetodoPagoClienteSerializer().fields
        self.assertNotIn('token', fields)


class LibroPuntosModelUnitTest(TestCase):

    def test_tipo_origen_choices_correctos(self):
        from clientes.models import LibroPuntos
        valores = [c[0] for c in LibroPuntos.TIPO_ORIGEN_CHOICES]
        self.assertEqual(
            set(valores),
            {'ORDEN_GANA', 'ORDEN_REDIME', 'AJUSTE_MANUAL', 'EXPIRACION'}
        )


class DireccionSerializadorUnitTest(TestCase):

    def _serializer(self, data):
        return DireccionUsuarioSerializer(data=data)

    def test_tipo_direccion_invalido_falla(self):
        s = self._serializer({'tipo_direccion': 'INVALIDO', 'codigo_pais': 'CO'})
        s.is_valid()
        self.assertIn('tipo_direccion', s.errors)

    def test_codigo_pais_mas_de_2_chars_falla(self):
        s = self._serializer({'tipo_direccion': 'ENVIO', 'codigo_pais': 'COL'})
        s.is_valid()
        self.assertIn('codigo_pais', s.errors)

    def test_codigo_pais_se_convierte_a_mayusculas(self):
        user = make_user('val@test.com')
        cliente = Cliente.objects.create(usuario=user)
        data = {
            'usuario': user.pk,
            'tipo_direccion': 'ENVIO',
            'nombre_destinatario': 'Test',
            'linea1': 'Calle 1',
            'ciudad': 'Bogotá',
            'codigo_pais': 'co',
        }
        s = DireccionUsuarioSerializer(data=data)
        s.is_valid()
        self.assertEqual(s.validated_data.get('codigo_pais', ''), 'CO')


class ClientePermissionsTest(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = make_admin()
        self.user = make_user()

    def test_admin_puede_listar(self):
        request = self.factory.get('/clientes/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_normal_recibe_403(self):
        request = self.factory.get('/clientes/')
        force_authenticate(request, user=self.user)
        view = ClienteViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_autenticado_recibe_401_o_403(self):
        request = self.factory.get('/clientes/')
        view = ClienteViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertIn(response.status_code, [401, 403])


class ClienteCRUDFunctionalTest(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = make_admin()
        self.cliente = make_cliente()

    def test_list_retorna_200(self):
        request = self.factory.get('/clientes/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_contiene_clientes(self):
        request = self.factory.get('/clientes/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'list'})
        response = view(request)
        self.assertGreaterEqual(len(response.data), 1)

    def test_retrieve_retorna_200(self):
        request = self.factory.get(f'/clientes/{self.cliente.pk}/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_inexistente_retorna_404(self):
        request = self.factory.get('/clientes/99999/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'retrieve'})
        response = view(request, pk=99999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_retorna_204(self):
        request = self.factory.delete(f'/clientes/{self.cliente.pk}/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_elimina_de_db(self):
        pk = self.cliente.pk
        request = self.factory.delete(f'/clientes/{pk}/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'delete': 'destroy'})
        view(request, pk=pk)
        self.assertFalse(Cliente.objects.filter(pk=pk).exists())

    def test_destroy_inexistente_retorna_404(self):
        request = self.factory.delete('/clientes/99999/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'delete': 'destroy'})
        response = view(request, pk=99999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_actualiza_fecha_nacimiento(self):
        data = {'fecha_nacimiento': '1995-08-20'}
        request = self.factory.patch(f'/clientes/{self.cliente.pk}/', data, format='json')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_actualiza_acepta_fidelizacion(self):
        data = {'acepta_fidelizacion': False}
        request = self.factory.patch(f'/clientes/{self.cliente.pk}/', data, format='json')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'patch': 'partial_update'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DireccionesFunctionalTest(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = make_admin()
        self.cliente = make_cliente()

    def test_action_direcciones_retorna_200(self):
        make_direccion(self.cliente)
        request = self.factory.get(f'/clientes/{self.cliente.pk}/direcciones/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'direcciones'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_direcciones_retorna_lista(self):
        make_direccion(self.cliente, tipo='ENVIO')
        make_direccion(self.cliente, tipo='FACTURA')
        request = self.factory.get(f'/clientes/{self.cliente.pk}/direcciones/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'direcciones'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(len(response.data), 2)

    def test_action_fidelizacion_retorna_200(self):
        make_cuenta_fidelizacion(self.cliente)
        request = self.factory.get(f'/clientes/{self.cliente.pk}/fidelizacion/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'fidelizacion'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_action_fidelizacion_retorna_puntos(self):
        make_cuenta_fidelizacion(self.cliente, puntos=500)
        request = self.factory.get(f'/clientes/{self.cliente.pk}/fidelizacion/')
        force_authenticate(request, user=self.admin)
        view = ClienteViewSet.as_view({'get': 'fidelizacion'})
        response = view(request, pk=self.cliente.pk)
        self.assertEqual(response.data['puntos_actuales'], 500)


class ClienteCreacionIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.client.force_authenticate(user=self.admin)

    def test_crear_cliente_via_api_persiste_en_bd(self):
        data = {
            'usuario': {
                'correo': 'nuevo@test.com',
                'password': 'pass1234',
            },
            'fecha_nacimiento': '1990-01-15',
            'acepta_fidelizacion': True,
        }
        response = self.client.post('/api/clientes/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cliente.objects.filter(usuario__correo='nuevo@test.com').exists())

    def test_crear_cliente_crea_usuario_con_password_hasheado(self):
        data = {
            'usuario': {
                'correo': 'hash@test.com',
                'password': 'pass1234',
            },
        }
        self.client.post('/api/clientes/', data, format='json')
        user = User.objects.get(correo='hash@test.com')
        self.assertTrue(user.check_password('pass1234'))

    def test_crear_cliente_asigna_rol_cliente(self):
        from usuarios.models import RolAcceso, UsuarioRol
        data = {
            'usuario': {
                'correo': 'rol@test.com',
                'password': 'pass1234',
            },
        }
        self.client.post('/api/clientes/', data, format='json')
        user = User.objects.get(correo='rol@test.com')
        tiene_rol = UsuarioRol.objects.filter(
            usuario=user, rol__codigo='CLIENTE'
        ).exists()
        self.assertTrue(tiene_rol)

    def test_eliminar_cliente_elimina_usuario_en_cascada(self):
        cliente = make_cliente('cascada@test.com')
        pk = cliente.pk
        usuario_id = cliente.usuario_id
        response = self.client.delete(f'/api/clientes/{pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cliente.objects.filter(pk=pk).exists())
        self.assertFalse(User.objects.filter(pk=usuario_id).exists())


class DireccionIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.client.force_authenticate(user=self.admin)
        self.cliente = make_cliente()

    def test_crear_direccion_via_api_persiste_en_bd(self):
        data = {
            'usuario': self.cliente.usuario_id,
            'tipo_direccion': 'ENVIO',
            'nombre_destinatario': 'María García',
            'linea1': 'Calle 80 # 45-12',
            'ciudad': 'Bogotá',
            'codigo_pais': 'CO',
        }
        response = self.client.post('/api/direcciones/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DireccionUsuario.objects.filter(usuario=self.cliente.usuario).exists()
        )

    def test_direccion_tipo_invalido_retorna_400(self):
        data = {
            'usuario': self.cliente.usuario_id,
            'tipo_direccion': 'INVALIDO',
            'nombre_destinatario': 'Test',
            'linea1': 'Calle 1',
            'ciudad': 'Bogotá',
            'codigo_pais': 'CO',
        }
        response = self.client.post('/api/direcciones/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filtro_por_usuario_retorna_solo_sus_direcciones(self):
        otro_cliente = make_cliente('otro@test.com')
        make_direccion(self.cliente, tipo='ENVIO')
        make_direccion(otro_cliente, tipo='FACTURA')
        response = self.client.get(
            f'/api/direcciones/?usuario={self.cliente.usuario_id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for dir_data in response.data:
            self.assertEqual(dir_data['usuario'], self.cliente.usuario_id)


class FidelizacionIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.client.force_authenticate(user=self.admin)
        self.cliente = make_cliente()
        self.cuenta = make_cuenta_fidelizacion(self.cliente, puntos=200)

    def test_cuenta_fidelizacion_se_refleja_en_api(self):
        response = self.client.get(
            f'/api/clientes/{self.cliente.pk}/fidelizacion/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['puntos_actuales'], 200)

    def test_movimiento_aparece_en_historial(self):
        LibroPuntos.objects.create(
            cliente=self.cliente,
            tipo_origen='ORDEN_GANA',
            puntos_delta=50,
            descripcion='Compra pedido #1',
        )
        response = self.client.get(
            f'/api/clientes/{self.cliente.pk}/fidelizacion/'
        )
        movimientos = response.data.get('movimientos', [])
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0]['puntos_delta'], 50)

    def test_cliente_sin_cuenta_fidelizacion_retorna_404(self):
        cliente_sin_cuenta = make_cliente('sincuenta@test.com')
        response = self.client.get(
            f'/api/clientes/{cliente_sin_cuenta.pk}/fidelizacion/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_total_ganados_y_redimidos_correctos(self):
        self.cuenta.total_ganados = 500
        self.cuenta.total_redimidos = 300
        self.cuenta.save()
        response = self.client.get(
            f'/api/clientes/{self.cliente.pk}/fidelizacion/'
        )
        self.assertEqual(response.data['total_ganados'], 500)
        self.assertEqual(response.data['total_redimidos'], 300)