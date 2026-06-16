from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from usuarios.models import Rol

from .forms import ProductoMaquillajeForm
from .models import ProductoMaquillaje


def make_rol_admin():
    rol, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
    return rol

def make_rol_cliente():
    rol, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
    return rol

def make_admin():
    return get_user_model().objects.create_user(
        email='admin@test.com',
        password='Pwd12345!',
        id_rol=make_rol_admin(),
        nombre1='Admin',
        is_superuser=True,
    )

def make_cliente_user():
    return get_user_model().objects.create_user(
        email='cliente@test.com',
        password='Pwd12345!',
        id_rol=make_rol_cliente(),
        nombre1='Cliente',
    )

def make_producto(nombre='Prod A', is_active=True, precio='10000'):
    return ProductoMaquillaje.objects.create(
        nombre=nombre,
        cantidad=10,
        estado='disponible',
        fecha_ingreso='2024-01-01',
        stock=5,
        precio=precio,
        descripcion='Descripción de prueba',
        marca='Marca Test',
        is_active=is_active,
    )

def make_gif_image(filename='test.gif'):
    img_bytes = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04'
        b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
    )
    return SimpleUploadedFile(filename, img_bytes, content_type='image/gif')

def base_payload(**overrides):
    data = {
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
    data.update(overrides)
    return data


class ProductoMaquillajeModelUnitTest(TestCase):

    def test_str_retorna_nombre(self):
        producto = make_producto(nombre='Labial Rojo')
        self.assertIn('Labial Rojo', str(producto))

    def test_is_active_default_es_true(self):
        field = ProductoMaquillaje._meta.get_field('is_active')
        self.assertTrue(field.default)

    def test_manager_activos_excluye_inactivos(self):
        make_producto(nombre='Activo', is_active=True)
        make_producto(nombre='Inactivo', is_active=False)
        activos = ProductoMaquillaje.activos.all()
        nombres = list(activos.values_list('nombre', flat=True))
        self.assertIn('Activo', nombres)
        self.assertNotIn('Inactivo', nombres)

    def test_precio_es_campo_decimal_o_char(self):
        producto = make_producto(precio='99999')
        producto.refresh_from_db()
        self.assertEqual(str(producto.precio).replace('.00', ''), '99999')

    def test_soft_delete_no_elimina_registro(self):
        producto = make_producto()
        pk = producto.pk
        producto.is_active = False
        producto.save()
        self.assertTrue(ProductoMaquillaje.objects.filter(pk=pk).exists())


class ProductoMaquillajeFormUnitTest(TestCase):

    def test_formulario_valido_con_datos_correctos(self):
        form = ProductoMaquillajeForm(data=base_payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_fecha_ingreso_futura_invalida(self):
        data = base_payload(
            fecha_ingreso=(timezone.now().date() + timedelta(days=1)).isoformat()
        )
        form = ProductoMaquillajeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_ingreso', form.errors)

    def test_fecha_ingreso_hoy_es_valida(self):
        data = base_payload(fecha_ingreso=timezone.now().date().isoformat())
        form = ProductoMaquillajeForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_requerido(self):
        data = base_payload(nombre='')
        form = ProductoMaquillajeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_precio_requerido(self):
        data = base_payload(precio='')
        form = ProductoMaquillajeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('precio', form.errors)

    def test_stock_negativo_invalido(self):
        data = base_payload(stock=-1)
        form = ProductoMaquillajeForm(data=data)
        self.assertFalse(form.is_valid())

    def test_descripcion_requerida(self):
        data = base_payload(descripcion='')
        form = ProductoMaquillajeForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('descripcion', form.errors)


class InventarioPermissionsFunctionalTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.cliente = make_cliente_user()

    def test_no_autenticado_redirige_a_login(self):
        response = self.client.get(reverse('lista_inventario'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_cliente_redirigido_desde_inventario(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('lista_inventario'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_admin_accede_a_lista_inventario(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('lista_inventario'))
        self.assertEqual(response.status_code, 200)

    def test_cliente_bloqueado_en_editar_producto(self):
        producto = make_producto()
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('editar_producto', args=[producto.id_inventario]))
        self.assertIn(response.status_code, [302, 403])

    def test_cliente_bloqueado_en_eliminar_producto(self):
        producto = make_producto()
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('eliminar_producto', args=[producto.id_inventario]))
        self.assertIn(response.status_code, [302, 403])


class InventarioListaFunctionalTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.producto_activo = make_producto(nombre='Prod Activo', is_active=True)
        self.producto_inactivo = make_producto(nombre='Prod Inactivo', is_active=False)

    def test_lista_muestra_solo_productos_activos(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('lista_inventario'))
        self.assertEqual(response.status_code, 200)
        productos = list(response.context['productos'])
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].id_inventario, self.producto_activo.id_inventario)

    def test_lista_no_muestra_productos_inactivos(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('lista_inventario'))
        nombres = [p.nombre for p in response.context['productos']]
        self.assertNotIn('Prod Inactivo', nombres)

    def test_lista_retorna_template_correcto(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('lista_inventario'))
        self.assertTemplateUsed(response, 'inventario/lista_inventario.html')


class InventarioEdicionFunctionalTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.producto = make_producto()
        self.producto_inactivo = make_producto(nombre='Inactivo', is_active=False)

    def test_editar_producto_inactivo_retorna_404(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('editar_producto', args=[self.producto_inactivo.id_inventario])
        )
        self.assertEqual(response.status_code, 404)

    def test_editar_producto_activo_retorna_200(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('editar_producto', args=[self.producto.id_inventario])
        )
        self.assertEqual(response.status_code, 200)

    def test_post_edicion_redirige(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            base_payload(nombre='Producto Editado'),
        )
        self.assertEqual(response.status_code, 302)

    def test_post_edicion_con_imagen_retorna_302(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            {**base_payload(nombre='Con Imagen'), 'imagen': make_gif_image()},
        )
        self.assertEqual(response.status_code, 302)


class InventarioEliminacionFunctionalTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.producto = make_producto()

    def test_eliminar_redirige(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('eliminar_producto', args=[self.producto.id_inventario])
        )
        self.assertEqual(response.status_code, 302)

    def test_eliminar_producto_inexistente_retorna_404(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('eliminar_producto', args=[99999]))
        self.assertEqual(response.status_code, 404)


class SoftDeleteIntegrationTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.producto = make_producto()

    def test_soft_delete_marca_inactivo_en_bd(self):
        self.client.force_login(self.admin)
        self.client.get(reverse('eliminar_producto', args=[self.producto.id_inventario]))
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.is_active)

    def test_soft_delete_excluye_de_manager_activos(self):
        self.client.force_login(self.admin)
        self.client.get(reverse('eliminar_producto', args=[self.producto.id_inventario]))
        self.assertFalse(
            ProductoMaquillaje.activos.filter(
                id_inventario=self.producto.id_inventario
            ).exists()
        )

    def test_soft_delete_registra_audit_log(self):
        self.client.force_login(self.admin)
        self.client.get(reverse('eliminar_producto', args=[self.producto.id_inventario]))
        self.assertTrue(
            AuditLog.objects.filter(
                action='inventario.soft_delete',
                object_id=str(self.producto.id_inventario),
            ).exists()
        )

    def test_soft_delete_no_elimina_registro_de_bd(self):
        pk = self.producto.id_inventario
        self.client.force_login(self.admin)
        self.client.get(reverse('eliminar_producto', args=[pk]))
        self.assertTrue(ProductoMaquillaje.objects.filter(pk=pk).exists())


class EdicionIntegrationTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.producto = make_producto()

    def test_edicion_persiste_nuevo_nombre_en_bd(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            base_payload(nombre='Nombre Actualizado'),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Nombre Actualizado')

    def test_edicion_registra_audit_log(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            base_payload(nombre='Auditado'),
        )
        self.assertTrue(
            AuditLog.objects.filter(action='inventario.update').exists()
        )

    def test_edicion_con_imagen_persiste_imagen_en_bd(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            {**base_payload(nombre='Con Imagen'), 'imagen': make_gif_image('edit.gif')},
        )
        self.producto.refresh_from_db()
        self.assertTrue(bool(self.producto.imagen))

    def test_edicion_con_imagen_registra_audit_log(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            {**base_payload(), 'imagen': make_gif_image('audit.gif')},
        )
        self.assertTrue(AuditLog.objects.filter(action='inventario.update').exists())

    def test_edicion_con_datos_invalidos_no_persiste(self):
        nombre_original = self.producto.nombre
        self.client.force_login(self.admin)
        self.client.post(
            reverse('editar_producto', args=[self.producto.id_inventario]),
            base_payload(nombre='', precio=''),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, nombre_original)