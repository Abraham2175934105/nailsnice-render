import io

import pandas as pd
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from .forms import ProductoMaquillajeForm
from .models import ProductoMaquillaje
from .services import save_producto_form, soft_delete_producto

INVENTARIO_COLUMNS = [
    ('id', 'ID'),
    ('nombre', 'Nombre'),
    ('cantidad', 'Cantidad'),
    ('descripcion', 'Descripción'),
    ('precio', 'Precio'),
    ('marca', 'Marca'),
    ('proveedor', 'Proveedor'),
    ('stock', 'Stock'),
    ('fecha_ingreso', 'Ingreso'),
    ('estado', 'Estado'),
]
INVENTARIO_DEFAULT_COLUMNS = ['id', 'nombre', 'marca', 'proveedor', 'stock', 'precio', 'estado']
PAGE_MIN = 10
PAGE_MAX = 30


def _build_inventory_rows(queryset, selected):
    config = {
        'id': ('ID', lambda p: p.id_inventario),
        'nombre': ('Nombre', lambda p: p.nombre),
        'cantidad': ('Cantidad', lambda p: p.cantidad),
        'stock': ('Stock', lambda p: p.stock),
        'precio': ('Precio', lambda p: p.precio),
        'marca': ('Marca', lambda p: p.marca),
        'proveedor': ('Proveedor', lambda p: p.proveedor),
        'estado': ('Estado', lambda p: p.estado),
        'fecha_ingreso': ('Fecha ingreso', lambda p: p.fecha_ingreso),
        'descripcion': ('Descripción', lambda p: p.descripcion),
    }
    keys = [k for k in selected if k in config] or ['id', 'nombre', 'marca', 'proveedor', 'stock', 'precio', 'estado']
    rows = []
    for p in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(p)
        rows.append(row)
    return rows


def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))


def _export_inventory(request, queryset, columns, fmt: str):
    rows = _build_inventory_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"inventario.{fmt}"
    if fmt == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return HttpResponse(buffer.getvalue(), content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'xlsx':
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'pdf':
        return build_crud_pdf_response(
            request=request,
            report_title='Reporte de Inventario',
            rows=rows,
            filename=filename,
        )
    return None


@admin_required
def lista_inventario(request):
    productos_qs = ProductoMaquillaje.activos.all().order_by('-fecha_ingreso', '-id_inventario')
    search = (request.GET.get('q') or '').strip()
    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(marca__icontains=search)
            | Q(proveedor__icontains=search)
            | Q(descripcion__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(productos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(INVENTARIO_COLUMNS)] or INVENTARIO_DEFAULT_COLUMNS
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
        response = _export_inventory(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'inventario/inventario.html', {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': INVENTARIO_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
    })

@admin_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoMaquillajeForm(request.POST, request.FILES)
        if form.is_valid():
            save_producto_form(form, user=request.user)
            return redirect('lista_inventario')
    else:
        form = ProductoMaquillajeForm()
    return render(request, 'inventario/formulario.html', {'form': form})

@admin_required
def editar_producto(request, id):
    producto = get_object_or_404(ProductoMaquillaje, id_inventario=id, is_active=True)
    if request.method == 'POST':
        form = ProductoMaquillajeForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            save_producto_form(form, user=request.user)
            return redirect('lista_inventario')
    else:
        form = ProductoMaquillajeForm(instance=producto)
    return render(request, 'inventario/formulario.html', {'form': form})

@admin_required
def eliminar_producto(request, id):
    producto = get_object_or_404(ProductoMaquillaje, id_inventario=id)
    soft_delete_producto(producto, user=request.user)
    return redirect('lista_inventario')


@admin_required
def cargar_inventario_masivo(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Debes adjuntar un archivo CSV o Excel.')
            return redirect('inventario_carga_masiva')

        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception:
            messages.error(request, 'No se pudo leer el archivo. Usa CSV o Excel válido.')
            return redirect('inventario_carga_masiva')

        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {'nombre', 'cantidad', 'stock', 'precio', 'marca', 'fecha_ingreso'}
        missing = required - set(df.columns)
        if missing:
            messages.error(request, f'Faltan columnas requeridas: {", ".join(sorted(missing))}')
            return redirect('inventario_carga_masiva')

        errores = []
        creados = 0
        for idx, row in df.iterrows():
            try:
                producto = ProductoMaquillaje(
                    nombre=str(row.get('nombre', '')).strip(),
                    cantidad=int(row.get('cantidad', 0) or 0),
                    stock=int(row.get('stock', 0) or 0),
                    precio=row.get('precio') or 0,
                    marca=str(row.get('marca', '') or 'Sin marca')[:100],
                    proveedor=str(row.get('proveedor', '') or 'Sin proveedor')[:120],
                    fecha_ingreso=row.get('fecha_ingreso'),
                    descripcion=str(row.get('descripcion', '') or '')[:255],
                    estado=str(row.get('estado', 'disponible')).lower() in ['disponible', 'activo'] and 'disponible' or 'no_disponible',
                )
                producto.full_clean()
                producto.save()
                creados += 1
            except Exception as exc:
                errores.append(f'Fila {idx + 1}: {exc}')

        if errores:
            messages.warning(request, f'Creados {creados}. Errores en filas: {len(errores)}')
        else:
            messages.success(request, f'Cargados {creados} productos correctamente.')
        return redirect('lista_inventario')

    return render(request, 'inventario/carga_masiva.html')