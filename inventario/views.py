import io
from decimal import Decimal

import pandas as pd  # type: ignore
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404

from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from productos.models import VarianteProducto, Producto
from .forms import VarianteProductoForm, SaldoInventarioForm, ProductoMaquillajeForm, MovimientoInventarioForm, ItemMovimientoForm
from .models import Bodega, SaldoInventario, ProductoMaquillaje, MovimientoInventario, TipoMovimientoInventario
from .services import save_producto_form, soft_delete_producto, registrar_movimiento

INVENTARIO_COLUMNS = [
    ('sku', 'SKU'),
    ('producto', 'Producto'),
    ('bodega', 'Bodega'),
    ('stock', 'Stock'),
    ('reservado', 'Reservado'),
    ('disponible', 'Disponible'),
    ('precio', 'Precio'),
    ('nivel_reorden', 'Reorden'),
    ('activo', 'Activo'),
]
INVENTARIO_DEFAULT_COLUMNS = ['sku', 'producto', 'bodega', 'stock', 'disponible', 'precio', 'activo']
PAGE_MIN = 10
PAGE_MAX = 30


def _ensure_default_bodega():
    bodega = Bodega.objects.filter(activo=True).order_by('id_bodega').first()
    if bodega:
        return bodega
    return Bodega.objects.create(codigo='PRINCIPAL', nombre='Bodega principal', activo=True)


def _build_inventory_rows(queryset, selected):
    config = {
        'sku': ('SKU', lambda s: s.variante.sku),
        'producto': ('Producto', lambda s: s.variante.producto.nombre),
        'bodega': ('Bodega', lambda s: s.bodega.nombre),
        'stock': ('Stock', lambda s: s.cantidad_existencia),
        'reservado': ('Reservado', lambda s: s.cantidad_reservada),
        'disponible': ('Disponible', lambda s: max(0, s.cantidad_existencia - s.cantidad_reservada)),
        'precio': ('Precio', lambda s: s.variante.precio),
        'nivel_reorden': ('Reorden', lambda s: s.nivel_reorden),
        'activo': ('Activo', lambda s: 'Si' if s.variante.activo else 'No'),
    }
    keys = [k for k in selected if k in config] or INVENTARIO_DEFAULT_COLUMNS
    rows = []
    for saldo in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(saldo)
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
    if ProductoMaquillaje.objects.exists():
        productos_qs = ProductoMaquillaje.activos.order_by('-creado_en')
        using_saldos = False
    else:
        productos_qs = (
            SaldoInventario.objects
            .select_related('variante__producto__marca', 'bodega')
            .order_by('-actualizado_en')
        )
        using_saldos = True
    search = (request.GET.get('q') or '').strip()
    if search:
        if using_saldos:
            productos_qs = productos_qs.filter(
                Q(variante__sku__icontains=search)
                | Q(variante__producto__nombre__icontains=search)
                | Q(variante__producto__marca__nombre__icontains=search)
                | Q(bodega__nombre__icontains=search)
                | Q(bodega__codigo__icontains=search)
            )
        else:
            productos_qs = productos_qs.filter(
                Q(nombre__icontains=search)
                | Q(marca__icontains=search)
                | Q(proveedor__icontains=search)
            )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(productos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    inventario_items = []
    if not using_saldos:
        for producto in page_obj.object_list:
            inventario_items.append({
                'id_variante': getattr(producto, 'id_inventario', None),
                'sku': None,
                'producto': producto.nombre,
                'bodega': None,
                'stock': producto.stock,
                'reservado': None,
                'disponible': producto.stock,
                'precio': producto.precio,
                'activo': producto.is_active,
            })
    else:
        for saldo in page_obj.object_list:
            disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0))
            inventario_items.append({
                'id_variante': saldo.variante.id_variante,
                'sku': saldo.variante.sku,
                'producto': saldo.variante.producto.nombre,
                'bodega': saldo.bodega.nombre,
                'stock': saldo.cantidad_existencia,
                'reservado': saldo.cantidad_reservada,
                'disponible': disponible,
                'nivel_reorden': saldo.nivel_reorden,
                'precio': saldo.variante.precio,
                'activo': saldo.variante.activo,
            })

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

    return render(request, 'inventario/lista_inventario.html', {
        'page_obj': page_obj,
        'productos': page_obj.object_list,
        'inventario_items': inventario_items,
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
    _ensure_default_bodega()
    if request.method == 'POST':
        variante_form = VarianteProductoForm(request.POST)
        saldo_form = SaldoInventarioForm(request.POST)
        if variante_form.is_valid() and saldo_form.is_valid():
            with transaction.atomic():
                variante = variante_form.save()
                saldo = saldo_form.save(commit=False)
                saldo.variante = variante
                saldo.save()
            return redirect('lista_inventario')
    else:
        variante_form = VarianteProductoForm()
        saldo_form = SaldoInventarioForm()
    return render(request, 'inventario/formulario.html', {
        'form_variante': variante_form,
        'form_saldo': saldo_form,
    })


@admin_required
def editar_producto(request, id):
    try:
        variante = VarianteProducto.objects.get(pk=id)
    except VarianteProducto.DoesNotExist:
        producto = get_object_or_404(ProductoMaquillaje, pk=id)
        if not producto.is_active:
            raise Http404()
        if request.method == 'POST':
            form = ProductoMaquillajeForm(request.POST, request.FILES, instance=producto)
            if form.is_valid():
                save_producto_form(form, user=request.user)
                return redirect('lista_inventario')
        else:
            form = ProductoMaquillajeForm(instance=producto)
        return render(request, 'inventario/formulario.html', {
            'form': form,
            'producto': producto,
        })

    saldo = SaldoInventario.objects.filter(variante=variante).first()
    if request.method == 'POST':
        variante_form = VarianteProductoForm(request.POST, instance=variante)
        saldo_form = SaldoInventarioForm(request.POST, instance=saldo)
        if variante_form.is_valid() and saldo_form.is_valid():
            with transaction.atomic():
                variante = variante_form.save()
                saldo = saldo_form.save(commit=False)
                saldo.variante = variante
                saldo.save()
            return redirect('lista_inventario')
    else:
        variante_form = VarianteProductoForm(instance=variante)
        saldo_form = SaldoInventarioForm(instance=saldo)
    return render(request, 'inventario/formulario.html', {
        'form_variante': variante_form,
        'form_saldo': saldo_form,
        'variante': variante,
    })


@admin_required
def eliminar_producto(request, id):
    try:
        variante = VarianteProducto.objects.get(pk=id)
        variante.activo = False
        variante.save(update_fields=['activo'])
        messages.info(request, 'Variante desactivada.')
        return redirect('lista_inventario')
    except VarianteProducto.DoesNotExist:
        producto = ProductoMaquillaje.objects.filter(pk=id).first()
        if not producto:
            return get_object_or_404(ProductoMaquillaje, pk=id)
        soft_delete_producto(producto, user=getattr(request, 'user', None))
        messages.info(request, 'Producto desactivado.')
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
        required = {'sku', 'producto', 'precio', 'stock', 'bodega'}
        missing = required - set(df.columns)
        if missing:
            messages.error(request, f'Faltan columnas requeridas: {", ".join(sorted(missing))}')
            return redirect('inventario_carga_masiva')

        errores = []
        creados = 0
        for idx, row in df.iterrows():
            try:
                nombre_producto = str(row.get('producto') or '').strip()
                if not nombre_producto:
                    raise ValueError('Producto requerido')

                producto = Producto.objects.filter(nombre__iexact=nombre_producto).first()
                if not producto:
                    raise ValueError('Producto no encontrado')

                sku = str(row.get('sku') or '').strip()
                if not sku:
                    raise ValueError('SKU requerido')

                bodega_raw = str(row.get('bodega') or '').strip()
                if not bodega_raw:
                    raise ValueError('Bodega requerida')

                bodega = Bodega.objects.filter(codigo__iexact=bodega_raw).first()
                if not bodega:
                    bodega = Bodega.objects.filter(nombre__iexact=bodega_raw).first()
                if not bodega:
                    bodega = Bodega.objects.create(
                        codigo=bodega_raw[:40],
                        nombre=bodega_raw[:120],
                        activo=True,
                    )

                precio = row.get('precio') or 0
                costo = row.get('costo') or 0
                stock = int(row.get('stock') or 0)
                reservado = int(row.get('reservado') or 0)
                nivel_reorden = int(row.get('nivel_reorden') or 0)
                codigo_barras = str(row.get('codigo_barras') or '').strip() or None
                nombre_variante = str(row.get('nombre_variante') or '').strip() or None

                variante, created = VarianteProducto.objects.get_or_create(
                    sku=sku,
                    defaults={
                        'producto': producto,
                        'codigo_barras': codigo_barras,
                        'nombre_variante': nombre_variante,
                        'precio': Decimal(str(precio)),
                        'costo': Decimal(str(costo)),
                        'activo': True,
                    },
                )
                if not created:
                    variante.producto = producto
                    variante.codigo_barras = codigo_barras
                    variante.nombre_variante = nombre_variante
                    variante.precio = Decimal(str(precio))
                    variante.costo = Decimal(str(costo))
                    variante.activo = True
                    variante.save()

                saldo, _ = SaldoInventario.objects.get_or_create(
                    variante=variante,
                    defaults={
                        'bodega': bodega,
                        'cantidad_existencia': stock,
                        'cantidad_reservada': reservado,
                        'nivel_reorden': nivel_reorden,
                    },
                )
                if saldo.bodega != bodega:
                    saldo.bodega = bodega
                saldo.cantidad_existencia = stock
                saldo.cantidad_reservada = reservado
                saldo.nivel_reorden = nivel_reorden
                saldo.save()

                creados += 1
            except Exception as exc:
                # CORRECCIÓN: Tratamos a idx de forma directa como string para satisfacer por completo a Pylance
                errores.append(f'Fila {str(idx)}: {exc}')

        if errores:
            messages.warning(request, f'Creados {creados}. Errores en filas: {len(errores)}')
        else:
            messages.success(request, f'Cargados {creados} registros correctamente.')
        return redirect('lista_inventario')

    return render(request, 'inventario/carga_masiva.html')


# ─── Vistas de Movimientos ────────────────────────────────────────────────────

@admin_required
def lista_movimientos(request):
    """Lista todos los movimientos con filtros por bodega, tipo y fecha."""
    qs = (
        MovimientoInventario.objects
        .select_related('tipo_movimiento', 'bodega', 'creado_por')
        .prefetch_related('items__variante__producto')
        .order_by('-creado_en')
    )

    # Filtros
    bodega_id = request.GET.get('bodega')
    tipo_id = request.GET.get('tipo')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if bodega_id:
        qs = qs.filter(bodega_id=bodega_id)
    if tipo_id:
        qs = qs.filter(tipo_movimiento_id=tipo_id)
    if fecha_desde:
        qs = qs.filter(creado_en__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(creado_en__date__lte=fecha_hasta)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventario/lista_movimientos.html', {
        'page_obj': page_obj,
        'movimientos': page_obj.object_list,
        'bodegas': Bodega.objects.filter(activo=True).order_by('nombre'),
        'tipos': TipoMovimientoInventario.objects.all().order_by('descripcion'),
        'filtros': {
            'bodega': bodega_id,
            'tipo': tipo_id,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        },
    })


@admin_required
def crear_movimiento(request):
    """Registra una entrada o salida de stock."""
    if request.method == 'POST':
        mov_form = MovimientoInventarioForm(request.POST)

        # Recogemos los items del POST (pueden venir varios)
        variantes = request.POST.getlist('variante')
        cantidades = request.POST.getlist('cantidad')
        costos = request.POST.getlist('costo_unitario')

        items = []
        item_errors = []
        for i, (v, c) in enumerate(zip(variantes, cantidades)):
            try:
                variante_id = int(v)
                cantidad = int(c)
                costo = costos[i] if i < len(costos) else None
                if cantidad <= 0:
                    raise ValueError('La cantidad debe ser mayor a 0')
                items.append({
                    'variante_id': variante_id,
                    'cantidad': cantidad,
                    'costo_unitario': costo or None,
                })
            except (ValueError, TypeError) as e:
                # CORRECCIÓN: Evitamos operaciones aritméticas sobre la variable de bucle i directamente
                item_errors.append(f'Item {str(i)}: {e}')

        if mov_form.is_valid() and items and not item_errors:
            try:
                tipo = mov_form.cleaned_data['tipo_movimiento']
                bodega = mov_form.cleaned_data['bodega']
                notas = mov_form.cleaned_data.get('notas')
                registrar_movimiento(
                    tipo_movimiento_id=tipo.pk,
                    bodega_id=bodega.pk,
                    items=items,
                    notas=notas,
                    user=request.user,
                )
                messages.success(request, 'Movimiento registrado correctamente.')
                return redirect('lista_movimientos')
            except Exception as e:
                messages.error(request, f'Error al registrar el movimiento: {e}')
        else:
            if not items:
                messages.error(request, 'Debes agregar al menos un item.')
            for err in item_errors:
                messages.error(request, err)
    else:
        mov_form = MovimientoInventarioForm()

    variantes_qs = VarianteProducto.objects.filter(activo=True).select_related('producto').order_by('producto__nombre')

    return render(request, 'inventario/crear_movimiento.html', {
        'mov_form': mov_form,
        'variantes': variantes_qs,
    })