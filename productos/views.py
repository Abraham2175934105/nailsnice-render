import io

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOrReadOnly
from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from .models import Producto, Categoria, Marca, Color, UnidadMedida
from .serializers import ProductoSerializer, CategoriaSerializer, MarcaSerializer, ColorSerializer, UnidadMedidaSerializer
from .forms import (
    CategoriaForm,
    MarcaForm,
    ColorForm,
    UnidadMedidaForm,
)


def _normalize_image_url(raw):
    value = str(raw or '').strip().replace('\\', '/')
    if not value:
        return None
    if value.startswith('http://') or value.startswith('https://'):
        return value

    media_url = settings.MEDIA_URL or '/media/'
    media_base = '/' + media_url.strip('/') + '/'

    if value.startswith('//'):
        value = '/' + value.lstrip('/')

    if value.startswith(media_base):
        while value.startswith(media_base):
            value = value[len(media_base):]
        value = value.lstrip('/')
        return f"{media_base}{value}" if value else None

    media_no_slash = media_base.lstrip('/')
    if value.startswith(media_no_slash):
        value = value[len(media_no_slash):].lstrip('/')
        return f"{media_base}{value}" if value else None

    if value.startswith('/'):
        return value

    return f"{media_base}{value}"


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


def _resolve_producto_image_url(request, producto):
    sources = []
    sources.extend(_image_candidates(getattr(producto, 'imagen', None)))

    inventario = getattr(producto, 'inventario', None)
    if inventario:
        sources.extend(_image_candidates(getattr(inventario, 'imagen', None)))

    for source in sources:
        normalized = _normalize_image_url(source)
        if not normalized:
            continue
        if normalized.startswith('http://') or normalized.startswith('https://'):
            return normalized
        return request.build_absolute_uri(normalized)
    return None

@ensure_csrf_cookie
def productos_page(request):
    # Vista HTML para mostrar todos los productos con filtros (frontend via fetch a la API DRF).
    cart = request.session.get('cart', {})
    return render(request, 'productos.html', {'cart': cart})


@ensure_csrf_cookie
def detalle_producto_page(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('id_categoria', 'id_marca', 'id_color', 'id_unidad_medida', 'inventario'),
        pk=producto_id,
    )

    inventario = producto.inventario
    stock_disponible = getattr(inventario, 'stock', 0) if inventario else 0

    def _to_payload(item):
        img = _resolve_producto_image_url(request, item)
        return {
            'id': item.id,
            'nombre': item.nombre,
            'descripcion': item.descripcion,
            'precio': str(item.precio),
            'imagen': img,
            'estado': item.estado_producto,
            'categoria': item.id_categoria.nombre_categoria if item.id_categoria else '',
            'marca': item.id_marca.nombre_marca if item.id_marca else '',
            'color': item.id_color.nombre_color if item.id_color else '',
            'unidad_medida': item.id_unidad_medida.nombre_medida if item.id_unidad_medida else '',
            'inventario_id': item.inventario_id,
            'stock': item.inventario.stock if item.inventario else 0,
        }

    relacionados_qs = (
        Producto.objects.select_related('id_categoria', 'id_marca', 'id_color', 'inventario')
        .filter(id_categoria=producto.id_categoria)
        .exclude(id=producto.id)
        [:4]
    )

    cart = request.session.get('cart', {})
    return render(request, 'detalle_producto.html', {
        'cart': cart,
        'producto': producto,
        'stock_disponible': stock_disponible,
        'productos_relacionados': relacionados_qs,
        'producto_payload': _to_payload(producto),
        'productos_relacionados_payload': [_to_payload(item) for item in relacionados_qs],
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


def buscar_productos_api(request):
    term = (request.GET.get('q') or '').strip()
    limit_raw = request.GET.get('limit', '8')
    try:
        limit = max(1, min(int(limit_raw), 20))
    except (TypeError, ValueError):
        limit = 8

    qs = Producto.objects.select_related('id_categoria', 'inventario').all()
    if term:
        qs = qs.filter(
            Q(nombre__icontains=term)
            | Q(descripcion__icontains=term)
            | Q(id_categoria__nombre_categoria__icontains=term)
            | Q(id_marca__nombre_marca__icontains=term)
        )

    productos = []
    for p in qs[:limit]:
        stock = p.inventario.stock if p.inventario else 0
        productos.append({
            'id': p.id,
            'nombre': p.nombre,
            'categoria': p.id_categoria.nombre_categoria if p.id_categoria else '',
            'precio': str(p.precio),
            'stock': stock,
            'disponible': stock > 0,
        })

    categorias = []
    categorias_qs = Categoria.objects.all()
    if term:
        categorias_qs = categorias_qs.filter(nombre_categoria__icontains=term)
    for c in categorias_qs[:6]:
        categorias.append({'id': c.id, 'nombre_categoria': c.nombre_categoria})

    return JsonResponse({
        'query': term,
        'productos': productos,
        'categorias': categorias,
    })


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
    ('unidad', 'Unidad'),
    ('inventario', 'Inventario'),
]
PRODUCTO_DEFAULT_COLUMNS = ['id', 'nombre', 'precio', 'estado_producto', 'categoria', 'inventario']


def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))


def _build_producto_rows(qs, selected):
    config = {
        'id': ('ID', lambda p: p.id),
        'nombre': ('Nombre', lambda p: p.nombre),
        'precio': ('Precio', lambda p: p.precio),
        'estado_producto': ('Estado', lambda p: p.estado_producto),
        'categoria': ('Categoría', lambda p: p.id_categoria.nombre_categoria if p.id_categoria else ''),
        'marca': ('Marca', lambda p: p.id_marca.nombre_marca if p.id_marca else ''),
        'color': ('Color', lambda p: p.id_color.nombre_color if p.id_color else ''),
        'unidad': ('Unidad', lambda p: p.id_unidad_medida.nombre_medida if p.id_unidad_medida else ''),
        'inventario': ('Inventario', lambda p: p.inventario.id_inventario if p.inventario else ''),
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
        Producto.objects.select_related('id_categoria', 'id_marca', 'id_color', 'id_unidad_medida', 'inventario')
    )
    search = (request.GET.get('q') or '').strip()
    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(descripcion__icontains=search)
            | Q(id_marca__nombre_marca__icontains=search)
            | Q(id_categoria__nombre_categoria__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(productos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(PRODUCTO_COLUMNS)] or PRODUCTO_DEFAULT_COLUMNS
    export_scope = (request.GET.get('export_scope') or 'page').lower()
    export_page = request.GET.get('export_page') or page_obj.number

    export_fmt = (request.GET.get('export') or '').lower()
    if export_fmt in {'csv', 'xlsx', 'pdf'}:
        export_source = productos_qs if export_scope == 'all' else paginator.get_page(export_page).object_list
        response = _export_productos(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'productos/catalogo.html', {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': PRODUCTO_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
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
            'categoria': (Categoria, CategoriaForm, 'nombre_categoria'),
            'marca': (Marca, MarcaForm, 'nombre_marca'),
            'color': (Color, ColorForm, 'nombre_color'),
            'unidad': (UnidadMedida, UnidadMedidaForm, 'nombre_medida'),
        }
        model_cls, form_cls, field_name = form_map.get(entity, (None, None, None))
        if model_cls and form_cls:
            instance = None
            if pk:
                instance = get_object_or_404(model_cls, pk=pk)
            form = form_cls(request.POST, instance=instance)
            if action == 'delete' and instance:
                instance.delete()
                mensaje_ok = f"{entity.title()} eliminada"
            elif form.is_valid():
                saved = form.save()
                mensaje_ok = f"{entity.title()} guardada: {getattr(saved, field_name)}"
            else:
                mensaje_err = form.errors.as_text()
        else:
            mensaje_err = 'Entidad no válida'

    context = {
        'categorias': Categoria.objects.order_by('nombre_categoria'),
        'marcas': Marca.objects.order_by('nombre_marca'),
        'colores': Color.objects.order_by('nombre_color'),
        'unidades': UnidadMedida.objects.order_by('nombre_medida'),
        'categoria_form': CategoriaForm(),
        'marca_form': MarcaForm(),
        'color_form': ColorForm(),
        'unidad_form': UnidadMedidaForm(),
        'mensaje_ok': mensaje_ok,
        'mensaje_err': mensaje_err,
    }
    return render(request, 'productos/atributos.html', context)

class ProductoViewSet(AuditViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'productos.producto'

class CategoriaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'productos.categoria'

class MarcaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'productos.marca'

class ColorViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'productos.color'

class UnidadMedidaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'productos.unidad_medida'
