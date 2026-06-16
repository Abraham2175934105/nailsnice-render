from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny

from core.audit import AuditViewSetMixin

from .forms import CategoriaForm, MarcaForm, SubcategoriaForm
from .models import (
    CategoriaCatalogo,
    ImagenProducto,
    MarcaCatalogo,
    Producto,
    SubcategoriaCatalogo,
    VarianteProducto,
)
from .serializers import (
    CategoriaCatalogoSerializer,
    MarcaCatalogoSerializer,
    ProductoSerializer,
)
from .views import CategoriaViewSet, MarcaViewSet, ProductoViewSet

User = get_user_model()


def make_admin(email='admin@test.com'):
    from usuarios.models import Rol
    rol, _ = Rol.objects.get_or_create(nombre=Rol.ADMIN)
    return User.objects.create_user(
        email=email, password='Pwd12345!', id_rol=rol,
        nombre1='Admin', is_superuser=True,
    )

def make_user(email='user@test.com'):
    from usuarios.models import Rol
    rol, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
    return User.objects.create_user(
        email=email, password='Pwd12345!', id_rol=rol, nombre1='User',
    )

def make_categoria(nombre='Labiales', slug=None):
    base_name = nombre
    base_slug = slug or nombre.lower().replace(' ', '-')
    if CategoriaCatalogo.objects.filter(nombre=nombre).exists() or CategoriaCatalogo.objects.filter(slug=base_slug).exists():
        counter = 1
        new_nombre = nombre
        new_slug = base_slug
        while CategoriaCatalogo.objects.filter(nombre=new_nombre).exists() or CategoriaCatalogo.objects.filter(slug=new_slug).exists():
            counter += 1
            new_nombre = f"{base_name} {counter}"
            new_slug = f"{base_slug}-{counter}"
        nombre = new_nombre
        slug = new_slug
    else:
        slug = base_slug
    return CategoriaCatalogo.objects.create(nombre=nombre, slug=slug)

def make_marca(nombre='MarcaTest'):
    return MarcaCatalogo.objects.create(nombre=nombre)

def make_subcategoria(categoria=None, nombre='Mate', slug=None):
    categoria = categoria or make_categoria()
    slug = slug or nombre.lower().replace(' ', '-')
    if SubcategoriaCatalogo.objects.filter(slug=slug, categoria=categoria).exists():
        base = slug
        counter = 1
        while SubcategoriaCatalogo.objects.filter(slug=slug, categoria=categoria).exists():
            counter += 1
            slug = f"{base}-{counter}"
    return SubcategoriaCatalogo.objects.create(
        categoria=categoria, nombre=nombre, slug=slug
    )

def make_producto(nombre='Labial Rojo', subcategoria=None, marca=None, estado='ACTIVO'):
    subcategoria = subcategoria or make_subcategoria()
    return Producto.objects.create(
        subcategoria=subcategoria,
        marca=marca,
        nombre=nombre,
        slug=nombre.lower().replace(' ', '-'),
        descripcion_corta='Desc corta',
        estado=estado,
    )

def make_variante(producto, sku='SKU-001', precio=Decimal('25000'), activo=True):
    return VarianteProducto.objects.create(
        producto=producto,
        sku=sku,
        precio=precio,
        activo=activo,
    )


class CategoriaCatalogoModelUnitTest(TestCase):

    def test_str_retorna_nombre(self):
        cat = make_categoria(nombre='Ojos')
        self.assertEqual(str(cat), 'Ojos')

    def test_activo_default_es_true(self):
        field = CategoriaCatalogo._meta.get_field('activo')
        self.assertTrue(field.default)

    def test_slug_unico(self):
        make_categoria(nombre='Cat A', slug='cat-a')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CategoriaCatalogo.objects.create(nombre='Cat B', slug='cat-a')

    def test_nombre_unico(self):
        make_categoria(nombre='Unica', slug='unica')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CategoriaCatalogo.objects.create(nombre='Unica', slug='unica-2')


class MarcaCatalogoModelUnitTest(TestCase):

    def test_str_retorna_nombre(self):
        marca = make_marca('NYX')
        self.assertEqual(str(marca), 'NYX')

    def test_activo_default_es_true(self):
        field = MarcaCatalogo._meta.get_field('activo')
        self.assertTrue(field.default)

    def test_nombre_unico(self):
        make_marca('MAC')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MarcaCatalogo.objects.create(nombre='MAC')


class SubcategoriaCatalogoModelUnitTest(TestCase):

    def test_str_retorna_nombre(self):
        sub = make_subcategoria(nombre='Brillosos')
        self.assertEqual(str(sub), 'Brillosos')

    def test_slug_unico(self):
        make_subcategoria(nombre='Sub A', slug='sub-a')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            cat = make_categoria(nombre='Cat2', slug='cat2')
            SubcategoriaCatalogo.objects.create(
                categoria=cat, nombre='Sub B', slug='sub-a'
            )

    def test_fk_categoria_restrict_al_borrar(self):
        sub = make_subcategoria()
        from django.db.models import RestrictedError
        with self.assertRaises(RestrictedError):
            sub.categoria.delete()


class ProductoModelUnitTest(TestCase):

    def test_str_retorna_nombre(self):
        p = make_producto(nombre='Base Líquida')
        self.assertEqual(str(p), 'Base Líquida')

    def test_estado_default_activo(self):
        field = Producto._meta.get_field('estado')
        self.assertEqual(field.default, 'ACTIVO')

    def test_slug_unico(self):
        make_producto()
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            sub = make_subcategoria(nombre='Sub2', slug='sub2')
            Producto.objects.create(
                subcategoria=sub, nombre='Prod B', slug='labial-rojo'
            )

    def test_marca_puede_ser_nula(self):
        p = make_producto(marca=None)
        self.assertIsNone(p.marca)

    def test_fk_subcategoria_restrict(self):
        p = make_producto()
        from django.db.models import RestrictedError
        with self.assertRaises(RestrictedError):
            p.subcategoria.delete()


class VarianteProductoModelUnitTest(TestCase):

    def test_str_retorna_sku(self):
        p = make_producto()
        v = make_variante(p, sku='SKU-TEST')
        self.assertEqual(str(v), 'SKU-TEST')

    def test_sku_unico(self):
        p = make_producto()
        make_variante(p, sku='SKU-DUP')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            VarianteProducto.objects.create(
                producto=p, sku='SKU-DUP', precio=Decimal('1000')
            )

    def test_activo_default_es_true(self):
        field = VarianteProducto._meta.get_field('activo')
        self.assertTrue(field.default)

    def test_cascade_al_borrar_producto(self):
        p = make_producto()
        v = make_variante(p)
        pk = v.pk
        p.delete()
        self.assertFalse(VarianteProducto.objects.filter(pk=pk).exists())


class ProductoViewSetUnitTest(TestCase):

    def test_queryset_apunta_a_producto(self):
        self.assertEqual(ProductoViewSet.queryset.model, Producto)

    def test_serializer_correcto(self):
        self.assertEqual(ProductoViewSet.serializer_class, ProductoSerializer)

    def test_audit_prefix_correcto(self):
        self.assertEqual(ProductoViewSet.audit_prefix, 'productos.producto')

    def test_hereda_audit_mixin(self):
        self.assertTrue(issubclass(ProductoViewSet, AuditViewSetMixin))

    def test_permission_es_public_read_only(self):
        self.assertIn(AllowAny, ProductoViewSet.permission_classes)

    def test_categoria_viewset_queryset(self):
        self.assertEqual(CategoriaViewSet.queryset.model, CategoriaCatalogo)

    def test_marca_viewset_queryset(self):
        self.assertEqual(MarcaViewSet.queryset.model, MarcaCatalogo)


class ProductoSerializerUnitTest(TestCase):

    def setUp(self):
        self.producto = make_producto()
        self.variante = make_variante(self.producto, precio=Decimal('30000'))

    def test_precio_retorna_precio_variante(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['precio'], '30000.00')

    def test_precio_retorna_cero_sin_variante(self):
        p = make_producto(nombre='Sin variante', subcategoria=make_subcategoria(
            nombre='SubX', slug='subx'
        ))
        s = ProductoSerializer(p)
        self.assertEqual(s.data['precio'], '0')

    def test_descripcion_usa_descripcion_corta(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['descripcion'], 'Desc corta')

    def test_estado_normalizado_activo(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['estado'], 'Activo')

    def test_id_marca_nulo_sin_marca(self):
        s = ProductoSerializer(self.producto)
        self.assertIsNone(s.data['id_marca'])

    def test_imagen_nula_sin_imagenes(self):
        s = ProductoSerializer(self.producto)
        self.assertIsNone(s.data['imagen'])

    def test_id_inventario_retorna_id_variante(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['id_inventario'], self.variante.id_variante)


class CategoriaFormUnitTest(TestCase):

    def test_formulario_valido(self):
        form = CategoriaForm(data={
            'nombre': 'Iluminadores',
            'slug': 'iluminadores',
            'descripcion': 'Desc',
            'activo': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_requerido(self):
        form = CategoriaForm(data={'nombre': '', 'slug': 'test', 'activo': True})
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_slug_requerido(self):
        form = CategoriaForm(data={'nombre': 'Test', 'slug': '', 'activo': True})
        self.assertFalse(form.is_valid())
        self.assertIn('slug', form.errors)


class MarcaFormUnitTest(TestCase):

    def test_formulario_valido(self):
        form = MarcaForm(data={'nombre': 'Maybelline', 'descripcion': '', 'activo': True})
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_requerido(self):
        form = MarcaForm(data={'nombre': '', 'activo': True})
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)


class SubcategoriaFormUnitTest(TestCase):

    def setUp(self):
        self.categoria = make_categoria(nombre='FormCat', slug='form-cat')

    def test_formulario_valido(self):
        form = SubcategoriaForm(data={
            'categoria': self.categoria.pk,
            'nombre': 'Gloss',
            'slug': 'gloss',
            'descripcion': '',
            'activo': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_categoria_requerida(self):
        form = SubcategoriaForm(data={
            'categoria': '',
            'nombre': 'Gloss',
            'slug': 'gloss',
            'activo': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('categoria', form.errors)


class ProductosPageFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_productos_page_retorna_200(self):
        response = self.client.get(reverse('productos'))
        self.assertEqual(response.status_code, 200)

    def test_productos_page_usa_template_correcto(self):
        response = self.client.get(reverse('productos'))
        self.assertTemplateUsed(response, 'productos.html')

    def test_productos_html_alias_retorna_200(self):
        response = self.client.get(reverse('productos_html'))
        self.assertEqual(response.status_code, 200)


class DetalleProductoFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.producto = make_producto()
        self.variante = make_variante(self.producto)

    def test_detalle_producto_retorna_200(self):
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detalle_producto_usa_template_correcto(self):
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.pk])
        )
        self.assertTemplateUsed(response, 'detalle_producto.html')

    def test_detalle_producto_inexistente_retorna_404(self):
        response = self.client.get(reverse('detalle_producto', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_detalle_producto_query_sin_id_redirige(self):
        response = self.client.get(reverse('detalle_producto_html'))
        self.assertEqual(response.status_code, 302)

    def test_detalle_producto_query_id_valido_retorna_200(self):
        response = self.client.get(
            reverse('detalle_producto_html') + f'?id={self.producto.pk}'
        )
        self.assertEqual(response.status_code, 200)

    def test_detalle_producto_contexto_contiene_producto(self):
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.pk])
        )
        self.assertEqual(response.context['producto'].pk, self.producto.pk)

    def test_detalle_producto_contexto_stock_disponible(self):
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.pk])
        )
        self.assertIn('stock_disponible', response.context)


class BuscarProductosFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.producto = make_producto(nombre='Labial Mate Rojo')
        make_variante(self.producto)

    def test_busqueda_retorna_200(self):
        response = self.client.get(reverse('api_productos_buscar'))
        self.assertEqual(response.status_code, 200)

    def test_busqueda_retorna_json(self):
        response = self.client.get(reverse('api_productos_buscar'))
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_busqueda_con_termino_filtra_productos(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=Labial')
        data = response.json()
        self.assertGreaterEqual(len(data['productos']), 1)
        nombres = [p['nombre'] for p in data['productos']]
        self.assertIn('Labial Mate Rojo', nombres)

    def test_busqueda_sin_resultados_retorna_lista_vacia(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=xyzinexistente')
        data = response.json()
        self.assertEqual(data['productos'], [])

    def test_busqueda_retorna_campo_query(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=test')
        data = response.json()
        self.assertIn('query', data)
        self.assertEqual(data['query'], 'test')

    def test_busqueda_limit_maximo_20(self):
        for i in range(25):
            sub = make_subcategoria(nombre=f'Sub{i}', slug=f'sub{i}')
            p = make_producto(nombre=f'Prod{i}', subcategoria=sub)
            make_variante(p, sku=f'SKU-{i}')
        response = self.client.get(reverse('api_productos_buscar') + '?limit=100')
        data = response.json()
        self.assertLessEqual(len(data['productos']), 20)


class CatalogoAdminFunctionalTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.user = make_user()

    def test_no_admin_redirigido_de_catalogo(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalogo_productos'))
        self.assertIn(response.status_code, [302, 403])

    def test_no_autenticado_redirigido_de_catalogo(self):
        response = self.client.get(reverse('catalogo_productos'))
        self.assertEqual(response.status_code, 302)

    def test_admin_accede_a_catalogo(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalogo_productos'))
        self.assertEqual(response.status_code, 200)

    def test_admin_accede_a_atributos(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalogo_atributos'))
        self.assertEqual(response.status_code, 200)

    def test_catalogo_usa_template_correcto(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalogo_productos'))
        self.assertTemplateUsed(response, 'productos/catalogo.html')

    def test_atributos_usa_template_correcto(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalogo_atributos'))
        self.assertTemplateUsed(response, 'productos/atributos.html')

    def test_crear_producto_redirige_a_inventario(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('catalogo_productos') + 'nuevo/')
        self.assertIn(response.status_code, [301, 302, 404])

    def test_csrf_token_api_retorna_ok(self):
        response = self.client.get(reverse('api_csrf_token'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))


class ProductoAPIFunctionalTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.user = make_user()
        self.producto = make_producto()
        make_variante(self.producto)

    def test_list_productos_retorna_200_anonimo(self):
        response = self.client.get('/api/productos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_categorias_retorna_200_anonimo(self):
        response = self.client.get('/api/categorias/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_marcas_retorna_200_anonimo(self):
        response = self.client.get('/api/marcas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_producto_retorna_200(self):
        response = self.client.get(f'/api/productos/{self.producto.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_producto_inexistente_retorna_404(self):
        response = self.client.get('/api/productos/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_viewset_es_solo_lectura_para_anonimo(self):
        response = self.client.post('/api/productos/', {'nombre': 'Nuevo'})
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ])


class CatalogoFiltrosIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.client.force_login(self.admin)

        self.cat_labiales = make_categoria(nombre='Labiales', slug='labiales')
        self.cat_ojos = make_categoria(nombre='Ojos', slug='ojos')
        self.sub_labiales = make_subcategoria(self.cat_labiales, 'Mate', 'mate')
        self.sub_ojos = make_subcategoria(self.cat_ojos, 'Sombras', 'sombras')

        self.prod_labial = make_producto('Labial Rojo', self.sub_labiales)
        self.prod_sombra = make_producto('Sombra Café', self.sub_ojos)
        make_variante(self.prod_labial, 'SKU-LAB', Decimal('25000'))
        make_variante(self.prod_sombra, 'SKU-SOM', Decimal('15000'))

    def test_catalogo_muestra_todos_los_productos(self):
        response = self.client.get(reverse('catalogo_productos'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.context['productos']), 2)

    def test_busqueda_filtra_por_nombre(self):
        response = self.client.get(reverse('catalogo_productos') + '?q=Labial')
        productos = response.context['productos']
        nombres = [p.nombre for p in productos]
        self.assertIn('Labial Rojo', nombres)
        self.assertNotIn('Sombra Café', nombres)

    def test_filtro_por_categoria(self):
        response = self.client.get(
            reverse('catalogo_productos') +
            f'?categorias={self.cat_ojos.pk}'
        )
        productos = response.context['productos']
        nombres = [p.nombre for p in productos]
        self.assertIn('Sombra Café', nombres)
        self.assertNotIn('Labial Rojo', nombres)

    def test_contexto_contiene_productos_data(self):
        response = self.client.get(reverse('catalogo_productos'))
        self.assertIn('productos_data', response.context)
        self.assertIsInstance(response.context['productos_data'], list)

    def test_contexto_contiene_columnas(self):
        response = self.client.get(reverse('catalogo_productos'))
        self.assertIn('columns_options', response.context)
        self.assertIn('selected_columns', response.context)


class ProductoRelacionesIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.marca = make_marca('L\'Oreal')
        self.categoria = make_categoria('Rostro', 'rostro')
        self.subcategoria = make_subcategoria(self.categoria, 'Base', 'base')
        self.producto = make_producto('Base Fluida', self.subcategoria, self.marca)
        self.variante = make_variante(self.producto, 'SKU-BASE', Decimal('45000'))

    def test_serializer_retorna_categoria_anidada(self):
        s = ProductoSerializer(self.producto)
        cat = s.data.get('categoria')
        self.assertIsNotNone(cat)
        self.assertEqual(cat['nombre_categoria'], 'Rostro')

    def test_serializer_retorna_marca_anidada(self):
        s = ProductoSerializer(self.producto)
        marca = s.data.get('marca')
        self.assertIsNotNone(marca)
        self.assertEqual(marca['nombre_marca'], "L'Oreal")

    def test_serializer_id_categoria_correcto(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['id_categoria'], self.categoria.pk)

    def test_serializer_id_marca_correcto(self):
        s = ProductoSerializer(self.producto)
        self.assertEqual(s.data['id_marca'], self.marca.pk)

    def test_detalle_incluye_productos_relacionados(self):
        prod2 = make_producto('Base Seca', self.subcategoria)
        make_variante(prod2, 'SKU-BASE2', Decimal('35000'))
        response = self.client.get(
            reverse('detalle_producto', args=[self.producto.pk])
        )
        self.assertIn('productos_relacionados', response.context)

    def test_imagen_producto_cascade_al_borrar(self):
        ImagenProducto.objects.create(
            producto=self.producto,
            ruta_almacenamiento='productos/test.jpg',
        )
        pk_img = ImagenProducto.objects.filter(producto=self.producto).first().pk
        self.producto.delete()
        self.assertFalse(ImagenProducto.objects.filter(pk=pk_img).exists())


class BusquedaIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.cat = make_categoria('Búsqueda Cat', 'busqueda-cat')
        self.sub = make_subcategoria(self.cat, 'Búsqueda Sub', 'busqueda-sub')
        self.marca = make_marca('BúsquedaMarca')
        self.prod = make_producto('Corrector Beige', self.sub, self.marca)
        make_variante(self.prod, 'SKU-COR', Decimal('22000'))

    def test_busqueda_por_nombre_retorna_producto(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=Corrector')
        data = response.json()
        nombres = [p['nombre'] for p in data['productos']]
        self.assertIn('Corrector Beige', nombres)

    def test_busqueda_por_marca_retorna_producto(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=BúsquedaMarca')
        data = response.json()
        nombres = [p['nombre'] for p in data['productos']]
        self.assertIn('Corrector Beige', nombres)

    def test_busqueda_por_categoria_retorna_producto(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=Búsqueda Cat')
        data = response.json()
        cat_nombres = [c['nombre_categoria'] for c in data['categorias']]
        self.assertIn('Búsqueda Cat', cat_nombres)

    def test_busqueda_retorna_disponibilidad(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=Corrector')
        data = response.json()
        self.assertIn('disponible', data['productos'][0])

    def test_busqueda_retorna_id_inventario(self):
        response = self.client.get(reverse('api_productos_buscar') + '?q=Corrector')
        data = response.json()
        self.assertIn('id_inventario', data['productos'][0])


class APIProductoIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.cat = make_categoria('API Cat', 'api-cat')
        self.sub = make_subcategoria(self.cat, 'API Sub', 'api-sub')
        self.marca = make_marca('APIMarca')
        self.producto = make_producto('Producto API', self.sub, self.marca)
        make_variante(self.producto, 'SKU-API', Decimal('55000'))

    def test_api_list_retorna_productos_correctos(self):
        response = self.client.get('/api/productos/')
        self.assertEqual(response.status_code, 200)
        nombres = [p['nombre'] for p in response.data['results']]
        self.assertIn('Producto API', nombres)

    def test_api_retrieve_retorna_precio_variante(self):
        response = self.client.get(f'/api/productos/{self.producto.pk}/')
        self.assertEqual(response.data['precio'], '55000.00')

    def test_api_retrieve_retorna_nombre_categoria(self):
        response = self.client.get(f'/api/productos/{self.producto.pk}/')
        self.assertEqual(response.data['categoria']['nombre_categoria'], 'API Cat')

    def test_api_retrieve_retorna_nombre_marca(self):
        response = self.client.get(f'/api/productos/{self.producto.pk}/')
        self.assertEqual(response.data['marca']['nombre_marca'], 'APIMarca')

    def test_api_list_categorias_incluye_categoria_creada(self):
        response = self.client.get('/api/categorias/')
        nombres = [c['nombre_categoria'] for c in response.data['results']]
        self.assertIn('API Cat', nombres)

    def test_api_list_marcas_incluye_marca_creada(self):
        response = self.client.get('/api/marcas/')
        nombres = [m['nombre_marca'] for m in response.data['results']]
        self.assertIn('APIMarca', nombres)