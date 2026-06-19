import io
from decimal import Decimal, InvalidOperation

import pandas as pd  # type: ignore
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Min
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_page
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from rest_framework import status
from django.utils.text import slugify

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOrReadOnly
from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from inventario.models import SaldoInventario
from .models import (
    Producto,
    CategoriaCatalogo,
    SubcategoriaCatalogo,
    MarcaCatalogo,
    VarianteProducto,
    ImagenProducto,
    AtributoDefinicion,
    OpcionAtributo,
    ReglaAtributoSubcategoria,
    ValorAtributoProducto,
    ValorAtributoVariante,
)
from .serializers import (
    ProductoSerializer,
    CategoriaCatalogoSerializer,
    MarcaCatalogoSerializer,
    SubcategoriaCatalogoSerializer,
)

PAGE_MIN = 10
PAGE_MAX = 30
PRODUCTO_COLUMNS = [
    ('id', 'ID'),
    ('nombre', 'Nombre'),
    ('precio', 'Precio'),
    ('estado_producto', 'Estado'),
    ('categoria', 'Categoría'),
    ('marca', 'Marca'),
    ('color', 'Color'),
    ('unit', 'Unidad'),
    ('inventario', 'Inventario'),
]
PRODUCTO_DEFAULT_COLUMNS = ['id', 'nombre', 'precio', 'estado_producto', 'categoria', 'inventario']


def _normalize_image_url(raw):
    value = str(raw or '').strip().replace('\\', '/')
    if not value:
        return None
    if value.startswith('http://') or value.startswith('https://'):
        return value

    media_url = (settings.MEDIA_URL or '/media/').rstrip('/') + '/'
    # Evitar doble prefijo /media//media/
    while value.startswith(media_url):
        value = value[len(media_url):]
    value = value.lstrip('/')
    return f"{media_url}{value}" if value else None


def _image_candidates(image_field):
    if not image_field:
        return []

    candidates = []
    name = getattr(image_field, 'name', None)
    if name:
        candidates.append(name)

    try:
        url = image_field.url
        if url:
            candidates.append(url)
    except Exception:
        pass

    raw = str(image_field or '').strip()
    if raw:
        candidates.append(raw)

    deduped = []
    seen = set()
    for item in candidates:
        text = str(item or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def _normalize_estado(estado):
    raw = str(estado or '').strip().upper()
    if raw in {'ACTIVO', 'ACTIVA'}:
        return 'Activo'
    if raw in {'INACTIVO', 'INACTIVA'}:
        return 'Inactivo'
    if raw in {'DESCONTINUADO', 'DESCONTINUADA'}:
        return 'Descontinuado'
    return estado or 'Activo'


def _get_variantes(producto):
    variantes = list(producto.variantes.all()) if hasattr(producto, 'variantes') else []
    if not variantes:
        return []
    activos = [v for v in variantes if getattr(v, 'activo', False)]
    return activos or variantes


def _get_default_variante(producto):
    variantes = _get_variantes(producto)
    if not variantes:
        return None
    return sorted(variantes, key=lambda v: v.precio or 0)[0]


def _get_stock_disponible(variante):
    if not variante:
        return 0
    saldo = getattr(variante, 'saldo_inventario', None)
    if not saldo:
        return 0
    return max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0))


def _get_producto_descripcion(producto):
    return producto.descripcion_corta or producto.descripcion_larga or producto.descripcion_tecnica or ''


def _iter_imagenes_product(producto):
    imagenes = getattr(producto, 'imagenes', None)
    if imagenes is None:
        return []
    return imagenes.all().order_by('-es_principal', 'orden', 'id_imagen')


def _resolve_producto_image_url(request, producto):
    sources = []
    for img in _iter_imagenes_product(producto):
        if img.ruta_almacenamiento:
            sources.append(img.ruta_almacenamiento)

    if not sources:
        for variante in _get_variantes(producto):
            # CORRECCIÓN PYLANCE: Verificación estricta del atributo dinámico de imágenes
            var_imagenes = getattr(variante, 'imagenes', None)
            if var_imagenes is not None:
                for img in var_imagenes.all():
                    if img.ruta_almacenamiento:
                        sources.append(img.ruta_almacenamiento)
            if sources:
                break

    for source in sources:
        normalized = _normalize_image_url(source)
        if not normalized:
            continue
        if normalized.startswith('http://') or normalized.startswith('https://'):
            return normalized
        return request.build_absolute_uri(normalized)
    return None


def _build_producto_payload(request, producto):
    variante = _get_default_variante(producto)
    stock = _get_stock_disponible(variante)
    categoria = None
    if getattr(producto, 'subcategoria', None):
        categoria = getattr(producto.subcategoria, 'categoria', None)
    return {
        'id': producto.id_producto,
        'nombre': producto.nombre,
        'descripcion': _get_producto_descripcion(producto),
        'precio': str(variante.precio) if variante else '0',
        'imagen': _resolve_producto_image_url(request, producto),
        'estado': _normalize_estado(producto.estado),
        'categoria': getattr(categoria, 'nombre', '') if categoria else '',
        'marca': getattr(producto.marca, 'nombre', '') if getattr(producto, 'marca', None) else '',
        'color': '',
        'unidad_medida': '',
        'inventario_id': getattr(variante, 'id_variante', None) if variante else None,
        'id_inventario': getattr(variante, 'id_variante', None) if variante else None,
        'stock': stock,
        'id_categoria': getattr(categoria, 'id_categoria', None) if categoria else None,
        'id_marca': getattr(producto.marca, 'id_marca', None) if getattr(producto, 'marca', None) else None,
    }


@cache_page(60 * 5)
@ensure_csrf_cookie
def productos_page(request):
    cart = request.session.get('cart', {})
    return render(request, 'productos.html', {'cart': cart})


@cache_page(60 * 5)
@ensure_csrf_cookie
def detalle_producto_page(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('subcategoria', 'subcategoria__categoria', 'marca')
        .prefetch_related('variantes', 'variantes__saldo_inventario', 'imagenes', 'variantes__imagenes'),
        pk=producto_id,
    )

    variante = _get_default_variante(producto)
    stock_disponible = _get_stock_disponible(variante)

    relacionados_qs = (
        Producto.objects.select_related('subcategoria', 'subcategoria__categoria', 'marca')
        .prefetch_related('variantes', 'variantes__saldo_inventario', 'imagenes', 'variantes__imagenes')
        .filter(subcategoria=producto.subcategoria)
        .exclude(id_producto=producto.id_producto)
        [:4]
    )

    cart = request.session.get('cart', {})
    return render(request, 'detalle_producto.html', {
        'cart': cart,
        'producto': producto,
        'stock_disponible': stock_disponible,
        'productos_relacionados': relacionados_qs,
        'producto_payload': _build_producto_payload(request, producto),
        'productos_relacionados_payload': [_build_producto_payload(request, item) for item in relacionados_qs],
    })


@ensure_csrf_cookie
def detalle_producto_page_query(request):
    raw_id = (request.GET.get('id') or '').strip()
    if not raw_id.isdigit():
        messages.error(request, 'Producto no valido.')
        return redirect('productos')
    return detalle_producto_page(request, int(raw_id))


@ensure_csrf_cookie
def csrf_token_api(request):
    return JsonResponse({'ok': True})


@cache_page(60 * 2)
def buscar_productos_api(request):
    term = (request.GET.get('q') or '').strip()
    limit_raw = request.GET.get('limit', '8')
    try:
        limit = max(1, min(int(limit_raw), 20))
    except (TypeError, ValueError):
        limit = 8

    qs = (
        Producto.objects
        .select_related('subcategoria', 'subcategoria__categoria', 'marca')
        .prefetch_related('variantes', 'variantes__saldo_inventario')
        .all()
    )
    if term:
        qs = qs.filter(
            Q(nombre__icontains=term)
            | Q(descripcion_corta__icontains=term)
            | Q(descripcion_larga__icontains=term)
            | Q(descripcion_tecnica__icontains=term)
            | Q(subcategoria__nombre__icontains=term)
            | Q(subcategoria__categoria__nombre__icontains=term)
            | Q(marca__nombre__icontains=term)
        )

    productos = []
    for p in qs[:limit]:
        variante = _get_default_variante(p)
        stock = _get_stock_disponible(variante)
        categoria = None
        if getattr(p, 'subcategoria', None):
            categoria = getattr(p.subcategoria, 'categoria', None)
        productos.append({
            'id': p.id_producto,
            'nombre': p.nombre,
            'categoria': getattr(categoria, 'nombre', '') if categoria else '',
            'precio': str(variante.precio) if variante else '0',
            'stock': stock,
            'disponible': stock > 0,
            'id_inventario': getattr(variante, 'id_variante', None) if variante else None,
            'inventario_id': getattr(variante, 'id_variante', None) if variante else None,
        })

    categorias = []
    categorias_qs = CategoriaCatalogo.objects.all()
    if term:
        categorias_qs = categorias_qs.filter(nombre__icontains=term)
    for c in categorias_qs[:6]:
        categorias.append({'id': c.id_categoria, 'nombre_categoria': c.nombre})

    return JsonResponse({
        'query': term,
        'productos': productos,
        'categorias': categorias,
    })


def _parse_decimal_filter(raw_value: str):
    raw_text = str(raw_value or '').strip().replace(',', '.')
    if not raw_text:
        return None
    try:
        parsed = Decimal(raw_text)
    except (InvalidOperation, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _build_producto_rows(qs, selected):
    # CORRECCIÓN PYLANCE: Extraemos de forma segura los valores evaluando que la variante por defecto no sea None
    def get_precio_seguro(p):
        v = _get_default_variante(p)
        return v.precio if v else 0

    def get_variante_id_segura(p):
        v = _get_default_variante(p)
        return v.id_variante if v else ''

    config = {
        'id': ('ID', lambda p: p.id_producto),
        'nombre': ('Nombre', lambda p: p.nombre),
        'precio': ('Precio', get_precio_seguro),
        'estado_producto': ('Estado', lambda p: _normalize_estado(p.estado)),
        'categoria': ('Categoria', lambda p: p.subcategoria.categoria.nombre if getattr(p, 'subcategoria', None) and getattr(p.subcategoria, 'categoria', None) else ''),
        'marca': ('Marca', lambda p: p.marca.nombre if getattr(p, 'marca', None) else ''),
        'color': ('Color', lambda p: ''),
        'unidad': ('Unidad', lambda p: ''),
        'inventario': ('Inventario', get_variante_id_segura),
    }
    keys = [k for k in selected if k in config] or PRODUCTO_DEFAULT_COLUMNS
    rows = []
    for p in qs:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(p)
        rows.append(row)
    return rows


def _export_productos(request, queryset, columns, fmt: str):
    rows = _build_producto_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"productos.{fmt}"
    if fmt == 'csv':
        buff = io.StringIO()
        df.to_csv(buff, index=False)
        return HttpResponse(buff.getvalue(), content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'xlsx':
        buff = io.BytesIO()
        df.to_excel(buff, index=False)
        buff.seek(0)
        return HttpResponse(buff.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'pdf':
        return build_crud_pdf_response(
            request=request,
            report_title='Reporte de Productos',
            rows=rows,
            filename=filename,
        )
    return None


@admin_required
def catalogo_productos(request):
    productos_qs = (
        Producto.objects.select_related('subcategoria', 'subcategoria__categoria', 'marca')
        .prefetch_related('variantes', 'variantes__saldo_inventario', 'imagenes', 'variantes__imagenes')
    )
    search = (request.GET.get('q') or '').strip()
    categorias_selected = [
        str(raw).strip() for raw in request.GET.getlist('categorias')
        if str(raw).strip().isdigit()
    ]
    categoria_legacy = (request.GET.get('categoria') or '').strip()
    if categoria_legacy.isdigit() and categoria_legacy not in categorias_selected:
        categorias_selected.append(categoria_legacy)

    precio_min_raw = (request.GET.get('precio_min') or '').strip()
    precio_max_raw = (request.GET.get('precio_max') or '').strip()
    orden_selected = (request.GET.get('orden') or 'recientes').strip().lower()

    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(descripcion_corta__icontains=search)
            | Q(descripcion_larga__icontains=search)
            | Q(marca__nombre__icontains=search)
            | Q(subcategoria__categoria__nombre__icontains=search)
        )

    if categorias_selected:
        productos_qs = productos_qs.filter(subcategoria__categoria__id_categoria__in=[int(value) for value in categorias_selected])

    precio_min = _parse_decimal_filter(precio_min_raw)
    precio_max = _parse_decimal_filter(precio_max_raw)
    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        precio_min, precio_max = precio_max, precio_min

    if precio_min is not None:
        productos_qs = productos_qs.filter(variantes__precio__gte=precio_min).distinct()
    if precio_max is not None:
        productos_qs = productos_qs.filter(variantes__precio__lte=precio_max).distinct()

    if orden_selected in {'precio_asc', 'precio_desc'}:
        productos_qs = productos_qs.annotate(min_precio=Min('variantes__precio'))

    order_map = {
        'recientes': ('-id_producto',),
        'precio_asc': ('min_precio', 'nombre'),
        'precio_desc': ('-min_precio', 'nombre'),
        'nombre_asc': ('nombre',),
        'nombre_desc': ('-nombre',),
        'categoria': ('subcategoria__categoria__nombre', 'nombre'),
    }
    if orden_selected not in order_map:
        orden_selected = 'recientes'
    
    productos_qs = productos_qs.order_by(*order_map[orden_selected])

    page_size = max(PAGE_MIN, min(PAGE_MAX, int(request.GET.get('page_size') or PAGE_MIN)))
    paginator = Paginator(productos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    productos_data = []
    for producto in page_obj.object_list:
        variante = _get_default_variante(producto)
        categoria = getattr(producto.subcategoria, 'categoria', None) if getattr(producto, 'subcategoria', None) else None
        productos_data.append({
            'id': producto.id_producto,
            'nombre': producto.nombre,
            'precio': str(variante.precio) if variante else '0',
            'estado_producto': _normalize_estado(producto.estado),
            'categoria': getattr(categoria, 'nombre', '') if categoria else '',
            'marca': getattr(producto.marca, 'nombre', '') if getattr(producto, 'marca', None) else '',
            'inventario_id': getattr(variante, 'id_variante', None) if variante else None,
            'stock': _get_stock_disponible(variante),
        })

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(PRODUCTO_COLUMNS)] or PRODUCTO_DEFAULT_COLUMNS
    export_scope = (request.GET.get('export_scope') or 'page').lower()
    if export_scope not in {'page', 'pages', 'all'}:
        export_scope = 'page'

    try:
        export_page = int(request.GET.get('export_page') or page_obj.number)
    except (TypeError, ValueError):
        export_page = page_obj.number
    export_page = max(1, min(export_page, paginator.num_pages or 1))

    export_pages = []
    for raw_page in request.GET.getlist('export_pages'):
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if 1 <= page_num <= (paginator.num_pages or 1):
            export_pages.append(page_num)
    export_pages = sorted(set(export_pages)) or [export_page]

    export_fmt = (request.GET.get('export') or '').lower()
    if export_fmt in {'csv', 'xlsx', 'pdf'}:
        if export_scope == 'all':
            export_source = productos_qs
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_productos(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'productos/catalogo.html', {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'productos_data': productos_data,
        'search': search,
        'page_size': page_size,
        'columns_options': PRODUCTO_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
        'categorias_selected': categorias_selected,
        'precio_min': precio_min_raw,
        'precio_max': precio_max_raw,
        'orden_selected': orden_selected,
        'categorias_export': CategoriaCatalogo.objects.order_by('nombre'),
    })


@admin_required
def crear_producto_catalogo(request):
    messages.info(request, 'La creacion de productos se gestiona desde Inventario.')
    return redirect('crear_producto')


@admin_required
def editar_producto_catalogo(request, pk):
    messages.info(request, 'La edicion de productos se gestiona desde Inventario.')
    return redirect('lista_inventario')


@admin_required
def desactivar_producto_catalogo(request, pk):
    messages.info(request, 'La gestion de estado de productos se realiza desde Inventario.')
    return redirect('lista_inventario')


@admin_required
def catalogo_atributos(request):
    mensaje_ok = None
    mensaje_err = None
    if request.method == 'POST':
        entity = request.POST.get('entity')
        action = request.POST.get('action')
        pk = request.POST.get('pk')

        form_map = {
            'categoria': (CategoriaCatalogo, None, 'nombre'),
            'marca': (MarcaCatalogo, None, 'nombre'),
        }
        model_cls, form_cls, field_name = form_map.get(entity, (None, None, None))
        if model_cls:
            instance = None
            if pk:
                instance = get_object_or_404(model_cls, pk=pk)
            if action == 'delete' and instance:
                instance.delete()
                mensaje_ok = f"{entity.title()} eliminada"
            else:
                mensaje_err = 'Operacion no soportada'
        else:
            mensaje_err = 'Entidad no valida'

    context = {
        'categorias': CategoriaCatalogo.objects.order_by('nombre'),
        'marcas': MarcaCatalogo.objects.order_by('nombre'),
        'colores': [],
        'unidades': [],
        'categoria_form': None,
        'marca_form': None,
        'color_form': None,
        'unidad_form': None,
        'mensaje_ok': mensaje_ok,
        'mensaje_err': mensaje_err,
    }
    return render(request, 'productos/atributos.html', context)


class ProductoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Producto.objects
        .select_related('subcategoria', 'subcategoria__categoria', 'marca')
        .prefetch_related('variantes', 'variantes__saldo_inventario', 'imagenes', 'variantes__imagenes')
    )
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]
    audit_prefix = 'productos.producto'
    http_method_names = ['get', 'head', 'options']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        subcategoria_id = data.get('id_subcategoria') or data.get('subcategoria')
        marca_id = data.get('id_marca') or data.get('id_marca')
        if not subcategoria_id:
            return Response({'error': 'La subcategoría es obligatoria.'}, status=status.HTTP_400_BAD_REQUEST)
        subcategoria = get_object_or_404(SubcategoriaCatalogo, pk=subcategoria_id)
        marca = MarcaCatalogo.objects.filter(pk=marca_id).first() if marca_id else None

        producto = Producto.objects.create(
            subcategoria=subcategoria,
            marca=marca,
            nombre=data.get('nombre'),
            slug=data.get('slug') or slugify(data.get('nombre') or ''),
            descripcion_corta=data.get('descripcion_corta'),
            descripcion_larga=data.get('descripcion_larga'),
            descripcion_tecnica=data.get('descripcion_tecnica'),
            estado=data.get('estado', 'ACTIVO'),
            creado_por=request.user if request.user.is_authenticated else None
        )

        variantes_data = data.get('variantes', [])
        for var_item in variantes_data:
            sku = var_item.get('sku')
            if not sku:
                return Response({'error': 'Cada variante debe tener un SKU único.'}, status=status.HTTP_400_BAD_REQUEST)
            VarianteProducto.objects.create(
                producto=producto,
                sku=sku,
                codigo_barras=var_item.get('codigo_barras'),
                nombre_variante=var_item.get('nombre_variante'),
                precio=Decimal(str(var_item.get('precio', '0'))),
                costo=Decimal(str(var_item.get('costo', '0'))),
                activo=var_item.get('activo', True),
            )

        serializer = self.get_serializer(producto)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoriaViewSet(AuditViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CategoriaCatalogo.objects.all()
    serializer_class = CategoriaCatalogoSerializer
    permission_classes = [AllowAny]
    audit_prefix = 'productos.categoria'


class MarcaViewSet(AuditViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MarcaCatalogo.objects.all()
    serializer_class = MarcaCatalogoSerializer
    permission_classes = [AllowAny]
    audit_prefix = 'productos.marca'


class ColorViewSet(viewsets.ViewSet):
    pass


class UnidadMedidaViewSet(viewsets.ViewSet):
    pass


# =========================================================================
# Vistas Web: CRUD para Atributos (Categorías y Marcas)
# =========================================================================

from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CategoriaForm, MarcaForm

class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = CategoriaCatalogo
    form_class = CategoriaForm
    template_name = 'productos/categoria_form.html'
    success_url = reverse_lazy('catalogos_admin')

    def form_valid(self, form):
        messages.success(self.request, "Categoría creada exitosamente.")
        return super().form_valid(form)

class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = CategoriaCatalogo
    form_class = CategoriaForm
    template_name = 'productos/categoria_form.html'
    success_url = reverse_lazy('catalogos_admin')

    def form_valid(self, form):
        messages.success(self.request, "Categoría actualizada exitosamente.")
        return super().form_valid(form)

class MarcaCreateView(LoginRequiredMixin, CreateView):
    model = MarcaCatalogo
    form_class = MarcaForm
    template_name = 'productos/marca_form.html'
    success_url = reverse_lazy('catalogos_admin')

    def form_valid(self, form):
        messages.success(self.request, "Marca creada exitosamente.")
        return super().form_valid(form)

class MarcaUpdateView(LoginRequiredMixin, UpdateView):
    model = MarcaCatalogo
    form_class = MarcaForm
    template_name = 'productos/marca_form.html'
    success_url = reverse_lazy('catalogos_admin')

    def form_valid(self, form):
        messages.success(self.request, "Marca actualizada exitosamente.")
        return super().form_valid(form)