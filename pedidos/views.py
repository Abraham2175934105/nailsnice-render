from datetime import date
from decimal import Decimal
import io
import re

import pandas as pd  # type: ignore

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML  # type: ignore

from core.auth import admin_required, employee_required
from core.pdf_reports import build_crud_pdf_response
from clientes.models import Cliente, DireccionUsuario
from inventario.models import SaldoInventario
from productos.models import VarianteProducto
from .forms import PedidoVentaForm, EmpleadoPedidoForm
from .models import PedidoVenta, DetallePedidoVenta, HistorialEstadoPedido
from .services import create_pedido_from_cart, create_transaccion


PEDIDOS_COLUMNS = [
    ('numero', 'Pedido'),
    ('cliente', 'Cliente'),
    ('estado', 'Estado'),
    ('total', 'Total'),
    ('fecha', 'Fecha'),
]
PEDIDOS_DEFAULT_COLUMNS = ['numero', 'cliente', 'estado', 'total', 'fecha']
PAGE_MIN = 10
PAGE_MAX = 30
DIRECCION_COLOMBIA_RE = re.compile(r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+')


def _is_valid_colombian_address(address: str) -> bool:
    return bool(DIRECCION_COLOMBIA_RE.match((address or '').strip()))


def _is_valid_card_number_luhn(number_digits: str) -> bool:
    if not number_digits or not number_digits.isdigit():
        return False

    checksum = 0
    reversed_digits = number_digits[::-1]
    for index, digit_char in enumerate(reversed_digits):
        digit = int(digit_char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _validate_card_payment_payload(payload) -> str | None:
    holder = (payload.get('card_holder') or '').strip()
    raw_number = str(payload.get('card_number') or '')
    number_digits = re.sub(r'\D', '', raw_number)
    expiry = (payload.get('card_expiry') or '').strip()
    cvv = re.sub(r'\D', '', str(payload.get('card_cvv') or ''))

    if not holder:
        return 'Ingresa el nombre del titular de la tarjeta.'
    if not re.fullmatch(r'[A-Za-z\s]{5,80}', holder):
        return 'El nombre del titular solo debe contener letras y espacios (5 a 80 caracteres).'

    if len(number_digits) < 13 or len(number_digits) > 19:
        return 'El número de tarjeta debe tener entre 13 y 19 dígitos.'
    if not _is_valid_card_number_luhn(number_digits):
        return 'El número de tarjeta no es válido.'

    expiry_match = re.fullmatch(r'(0[1-9]|1[0-2])\s*/\s*(\d{2})', expiry)
    if not expiry_match:
        return 'La fecha de expiración debe tener formato MM/AA.'

    month = int(expiry_match.group(1))
    year = 2000 + int(expiry_match.group(2))
    today = date.today()
    if (year, month) < (today.year, today.month):
        return 'La tarjeta está vencida.'

    if not re.fullmatch(r'\d{3,4}', cvv):
        return 'El CVV debe tener 3 o 4 dígitos.'

    return None


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


def _resolve_cart_image_url(request, variante):
    if not variante:
        return None

    if getattr(variante, 'producto', None) and getattr(variante.producto, 'imagen', None):
        try:
            url = variante.producto.imagen.url
            if url:
                return url
        except Exception:
            pass

    sources = []
    imagenes = getattr(variante, 'imagenes', None)
    if imagenes is not None:
        for img in imagenes.all().order_by('-es_principal', 'orden', 'id_imagen'):
            if img.ruta_almacenamiento:
                sources.append(img.ruta_almacenamiento)

    if not sources and getattr(variante, 'producto', None):
        producto_imagenes = getattr(variante.producto, 'imagenes', None)
        if producto_imagenes is not None:
            for img in producto_imagenes.all().order_by('-es_principal', 'orden', 'id_imagen'):
                if img.ruta_almacenamiento:
                    sources.append(img.ruta_almacenamiento)

    for source in sources:
        normalized = _normalize_image_url(source)
        if not normalized:
            continue
        if normalized.startswith('http://') or normalized.startswith('https://'):
            return normalized
        return request.build_absolute_uri(normalized)
    return None


def _get_user_shipping_address(user) -> dict:
    direccion = (
        DireccionUsuario.objects
        .filter(usuario=user, es_predeterminada_envio=True)
        .order_by('-actualizado_en')
        .first()
    )
    if not direccion:
        direccion = DireccionUsuario.objects.filter(usuario=user).order_by('-actualizado_en').first()
    if not direccion:
        return {}
    return {
        'linea1': direccion.linea1,
        'linea2': direccion.linea2 or '',
        'ciudad': direccion.ciudad,
        'departamento': direccion.departamento or '',
        'codigo_postal': direccion.codigo_postal or '',
        'nombre_destinatario': direccion.nombre_destinatario or '',
    }


def _sync_user_shipping_address(user, direccion_data: dict):
    """Sincroniza la dirección de envío del checkout con el perfil del usuario.
    Si el usuario no tiene perfil de cliente (sin OneToOne perfil_cliente),
    la operación se omite silenciosamente para no bloquear el pedido.
    """
    try:
        linea1 = (direccion_data.get('linea1') or '').strip()
        ciudad = (direccion_data.get('ciudad') or '').strip()
        if not linea1 or not ciudad:
            return

        direccion = DireccionUsuario.objects.filter(usuario=user, es_predeterminada_envio=True).first()
        if direccion:
            direccion.linea1 = linea1
            direccion.linea2 = (direccion_data.get('linea2') or '').strip() or None
            direccion.ciudad = ciudad
            direccion.departamento = (direccion_data.get('departamento') or '').strip() or None
            direccion.codigo_postal = (direccion_data.get('codigo_postal') or '').strip() or None
            direccion.nombre_destinatario = (direccion_data.get('nombre_destinatario') or direccion.nombre_destinatario)
            direccion.save()
            return

        DireccionUsuario.objects.create(
            usuario=user,
            tipo_direccion='ENVIO',
            etiqueta='Checkout',
            nombre_destinatario=(direccion_data.get('nombre_destinatario') or user.correo)[:120],
            linea1=linea1[:160],
            linea2=(direccion_data.get('linea2') or '').strip()[:160] or None,
            ciudad=ciudad[:80],
            departamento=(direccion_data.get('departamento') or '').strip()[:80] or None,
            codigo_postal=(direccion_data.get('codigo_postal') or '').strip()[:20] or None,
            codigo_pais='CO',
            es_predeterminada_envio=True,
            es_predeterminada_factura=False,
        )
    except Exception:
        # El pedido ya fue creado; fallar en sincronizar la dirección no debe revertirlo.
        pass


def inicio(request):
    return render(request, 'pedidos/index.html')


def _build_pedidos_rows(queryset, selected):
    config = {
        'numero': ('Pedido', lambda p: p.numero_pedido or p.id_pedido),
        'cliente': ('Cliente', lambda p: p.cliente.usuario.correo),
        'estado': ('Estado', lambda p: p.estado),
        'total': ('Total', lambda p: p.monto_total),
        'fecha': ('Fecha', lambda p: p.realizado_en),
    }
    keys = [k for k in selected if k in config] or PEDIDOS_DEFAULT_COLUMNS
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


def _export_pedidos(request, queryset, columns, fmt: str):
    rows = _build_pedidos_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"pedidos.{fmt}"
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
            report_title='Reporte de Pedidos',
            rows=rows,
            filename=filename,
        )
    return None


@admin_required
def lista_pedidos(request):
    pedidos_qs = (
        PedidoVenta.objects
        .select_related('cliente__usuario')
        .order_by('-realizado_en')
    )
    search = (request.GET.get('q') or '').strip()
    if search:
        pedidos_qs = pedidos_qs.filter(
            Q(numero_pedido__icontains=search)
            | Q(cliente__usuario__correo__icontains=search)
            | Q(cliente__usuario__nombre__icontains=search)
            | Q(cliente__usuario__apellido__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(pedidos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(PEDIDOS_COLUMNS)] or PEDIDOS_DEFAULT_COLUMNS
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
            export_source = pedidos_qs.iterator(chunk_size=2000)
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_pedidos(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'pedidos/pedidos.html', {
        'page_obj': page_obj,
        'pedidos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': PEDIDOS_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
    })


@admin_required
def crear_pedido(request):
    if request.method == 'POST':
        form = PedidoVentaForm(request.POST)
        if form.is_valid():
            cliente = form.cleaned_data['cliente']
            variante = form.cleaned_data['variante']
            cantidad = form.cleaned_data['cantidad']
            direccion_data = {
                'linea1': form.cleaned_data['direccion_linea1'],
                'ciudad': form.cleaned_data['ciudad'],
                'departamento': form.cleaned_data.get('departamento'),
                'nombre_destinatario': form.cleaned_data.get('nombre_destinatario'),
            }
            create_pedido_from_cart(
                request.user,
                [{'variante': variante, 'cantidad': cantidad}],
                direccion_data,
                'manual',
                cliente=cliente,
                estado=form.cleaned_data['estado'],
            )
            return redirect('lista_pedidos')
    else:
        form = PedidoVentaForm()
    return render(request, 'pedidos/formulario.html', {'form': form, 'is_edit': False})


@admin_required
def editar_pedido(request, id):
    pedido = get_object_or_404(PedidoVenta, id_pedido=id)
    # CORRECCIÓN PYLANCE: Consulta directa mediante el modelo para saltar el atributo inverso dinámico '.detalles'
    detalle = DetallePedidoVenta.objects.filter(pedido=pedido).select_related('variante').first()
    direccion = pedido.direccion_envio
    initial = {
        'cliente': pedido.cliente,
        'variante': detalle.variante if detalle else None,
        'cantidad': detalle.cantidad if detalle else 1,
        'direccion_linea1': getattr(direccion, 'linea1', ''),
        'ciudad': getattr(direccion, 'ciudad', ''),
        'departamento': getattr(direccion, 'departamento', ''),
        'nombre_destinatario': getattr(direccion, 'nombre_destinatario', ''),
        'estado': pedido.estado,
    }
    if request.method == 'POST':
        form = PedidoVentaForm(request.POST)
        form.fields['cliente'].disabled = True
        form.fields['variante'].disabled = True
        form.fields['cantidad'].disabled = True
        if form.is_valid():
            nuevo_estado = form.cleaned_data['estado']
            if pedido.estado != nuevo_estado:
                from .services import cambiar_estado_pedido
                cambiar_estado_pedido(pedido, nuevo_estado, request.user, 'Cambio de estado desde panel')
            if pedido.direccion_envio:
                pedido.direccion_envio.linea1 = form.cleaned_data['direccion_linea1']
                pedido.direccion_envio.ciudad = form.cleaned_data['ciudad']
                pedido.direccion_envio.departamento = form.cleaned_data.get('departamento') or None
                pedido.direccion_envio.nombre_destinatario = form.cleaned_data.get('nombre_destinatario') or pedido.direccion_envio.nombre_destinatario
                pedido.direccion_envio.save()
            return redirect('lista_pedidos')
    else:
        form = PedidoVentaForm(initial=initial)
        form.fields['cliente'].disabled = True
        form.fields['variante'].disabled = True
        form.fields['cantidad'].disabled = True
    return render(request, 'pedidos/formulario.html', {'form': form, 'is_edit': True, 'pedido': pedido})


@admin_required
def eliminar_pedido(request, id):
    pedido = get_object_or_404(PedidoVenta, id_pedido=id)
    pedido.estado = 'CANCELADO'
    pedido.save(update_fields=['estado', 'actualizado_en'])
    return redirect('lista_pedidos')


def _employee_owner_key(user):
    return str(getattr(user, 'correo', '') or '').strip().lower()


def _employee_display_name(user):
    nombre = str(getattr(user, 'nombre', '') or '').strip()
    apellido = str(getattr(user, 'apellido', '') or '').strip()
    return f"{nombre} {apellido}".strip()


@employee_required
def empleado_lista_pedidos(request):
    cliente = Cliente.objects.filter(usuario=request.user).first()
    pedidos_qs = PedidoVenta.objects.none()
    if cliente:
        pedidos_qs = (
            PedidoVenta.objects
            .filter(cliente=cliente)
            .select_related('cliente__usuario')
            .order_by('-realizado_en')
        )

    search = (request.GET.get('q') or '').strip()
    if search:
        pedidos_qs = pedidos_qs.filter(
            Q(numero_pedido__icontains=search)
            | Q(estado__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(pedidos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'empleado/pedidos.html', {
        'page_obj': page_obj,
        'pedidos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
    })


@employee_required
def empleado_crear_pedido(request):
    owner_email = _employee_owner_key(request.user)
    owner_name = _employee_display_name(request.user)
    if request.method == 'POST':
        form = EmpleadoPedidoForm(request.POST)
        if form.is_valid():
            cliente = Cliente.objects.get_or_create(usuario=request.user)[0]
            variante = form.cleaned_data['variante']
            cantidad = form.cleaned_data['cantidad']
            direccion_data = {
                'linea1': form.cleaned_data['direccion_linea1'],
                'ciudad': form.cleaned_data['ciudad'],
                'departamento': form.cleaned_data.get('departamento'),
                'nombre_destinatario': form.cleaned_data.get('nombre_destinatario'),
            }
            create_pedido_from_cart(
                request.user,
                [{'variante': variante, 'cantidad': cantidad}],
                direccion_data,
                'manual',
                cliente=cliente,
                estado=form.cleaned_data['estado'],
            )
            messages.success(request, f'Pedido registrado correctamente para {owner_name or owner_email}.')
            return redirect('empleado_pedidos')
        messages.error(request, 'Corrige los errores del formulario para registrar el pedido.')
    else:
        form = EmpleadoPedidoForm()

    return render(request, 'empleado/pedido_form.html', {
        'form': form,
        'is_edit': False,
    })


@employee_required
def empleado_editar_pedido(request, id):
    owner_email = _employee_owner_key(request.user)
    cliente = Cliente.objects.filter(usuario=request.user).first()
    pedido = get_object_or_404(PedidoVenta, id_pedido=id, cliente=cliente)
    # CORRECCIÓN PYLANCE: Igualmente, resolvemos a través de DetallePedidoVenta explícitamente
    detalle = DetallePedidoVenta.objects.filter(pedido=pedido).select_related('variante').first()
    direccion = pedido.direccion_envio
    initial = {
        'variante': detalle.variante if detalle else None,
        'cantidad': detalle.cantidad if detalle else 1,
        'direccion_linea1': getattr(direccion, 'linea1', ''),
        'ciudad': getattr(direccion, 'ciudad', ''),
        'departamento': getattr(direccion, 'departamento', ''),
        'nombre_destinatario': getattr(direccion, 'nombre_destinatario', ''),
        'estado': pedido.estado,
    }
    if request.method == 'POST':
        form = EmpleadoPedidoForm(request.POST)
        form.fields['variante'].disabled = True
        form.fields['cantidad'].disabled = True
        if form.is_valid():
            nuevo_estado = form.cleaned_data['estado']
            if pedido.estado != nuevo_estado:
                from .services import cambiar_estado_pedido
                cambiar_estado_pedido(pedido, nuevo_estado, request.user, 'Cambio de estado desde panel')
            if pedido.direccion_envio:
                pedido.direccion_envio.linea1 = form.cleaned_data['direccion_linea1']
                pedido.direccion_envio.ciudad = form.cleaned_data['ciudad']
                pedido.direccion_envio.departamento = form.cleaned_data.get('departamento') or None
                pedido.direccion_envio.nombre_destinatario = form.cleaned_data.get('nombre_destinatario') or pedido.direccion_envio.nombre_destinatario
                pedido.direccion_envio.save()
            messages.success(request, 'Pedido actualizado correctamente.')
            return redirect('empleado_pedidos')
        messages.error(request, 'Corrige los errores del formulario para actualizar el pedido.')
    else:
        form = EmpleadoPedidoForm(initial=initial)
        form.fields['variante'].disabled = True
        form.fields['cantidad'].disabled = True

    return render(request, 'empleado/pedido_form.html', {
        'form': form,
        'is_edit': True,
        'pedido': pedido,
    })


@employee_required
def empleado_eliminar_pedido(request, id):
    owner_email = _employee_owner_key(request.user)
    cliente = Cliente.objects.filter(usuario=request.user).first()
    pedido = get_object_or_404(PedidoVenta, id_pedido=id, cliente=cliente)
    pedido.estado = 'CANCELADO'
    pedido.save(update_fields=['estado', 'actualizado_en'])
    messages.info(request, 'Pedido eliminado.')
    return redirect('empleado_pedidos')


# --- Carrito y checkout (Phase C) ---

def _get_cart(session):
    return session.get('cart', {})


def _save_cart(session, cart):
    session['cart'] = cart
    session.modified = True


def _cart_count(cart):
    return sum(int(val) for val in cart.values()) if cart else 0


@login_required
def cart_add(request, product_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405) if is_ajax else redirect('carrito')

    variante = get_object_or_404(VarianteProducto, pk=product_id, activo=True)
    try:
        qty = int(request.POST.get('cantidad', '1'))
    except ValueError:
        qty = 1

    if qty < 1:
        qty = 1
    if qty > 10:
        qty = 10

    cart = _get_cart(request.session)
    current = cart.get(str(product_id), 0)
    new_qty = current + qty

    if new_qty > 10:
        new_qty = 10
        messages.warning(request, 'Máximo 10 unidades por producto.')

    saldo = SaldoInventario.objects.filter(variante=variante).first()
    disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0)) if saldo else 0
    if new_qty > disponible:
        error_msg = 'No hay stock suficiente para esa cantidad.'
        if is_ajax:
            return JsonResponse({'ok': False, 'error': error_msg, 'cart_count': _cart_count(cart)}, status=400)
        messages.error(request, error_msg)
        return redirect('productos')

    cart[str(product_id)] = new_qty
    _save_cart(request.session, cart)
    count = _cart_count(cart)
    if is_ajax:
        return JsonResponse({'ok': True, 'cart_count': count})
    messages.success(request, 'Producto agregado al carrito.')
    return redirect('carrito')


@login_required
def cart_view(request):
    cart = _get_cart(request.session)
    items = []
    total = Decimal('0')
    cart_changed = False

    if cart:
        variantes = (
            VarianteProducto.objects
            .filter(id_variante__in=[int(pid) for pid in cart.keys()], activo=True)
            .select_related('producto')
            .prefetch_related('imagenes', 'producto__imagenes')
        )
        # CORRECCIÓN PYLANCE: Acceso estricto tipado usando 'saldo.variante.id_variante' en vez de propiedad mágica latente
        saldo_map = {
            saldo.variante.id_variante: saldo
            for saldo in SaldoInventario.objects
                .filter(variante__id_variante__in=[v.id_variante for v in variantes])
                .select_related('variante')
                .only('variante__id_variante', 'cantidad_existencia', 'cantidad_reservada')
        }
        map_prod = {v.id_variante: v for v in variantes}
        for pid, qty in list(cart.items()):
            prod = map_prod.get(int(pid))
            if not prod:
                cart.pop(str(pid), None)
                cart_changed = True
                continue

            qty_int = int(qty)
            saldo = saldo_map.get(prod.id_variante)
            disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0)) if saldo else 0
            if disponible <= 0:
                cart.pop(str(pid), None)
                cart_changed = True
                continue
            if qty_int > disponible:
                qty_int = disponible
                cart[str(pid)] = qty_int
                cart_changed = True

            subtotal = Decimal(prod.precio) * qty_int
            total += subtotal
            items.append({
                'producto': prod.producto,
                'variante': prod,
                'cantidad': qty_int,
                'subtotal': subtotal,
                'precio_unitario': prod.precio,
                'stock_disponible': disponible,
                'inventario_id': prod.id_variante,
                'imagen_url': _resolve_cart_image_url(request, prod),
            })

    if cart_changed:
        _save_cart(request.session, cart)
        messages.info(request, 'Se ajustaron cantidades del carrito según stock disponible.')

    return render(request, 'carrito.html', {
        'items': items,
        'total': total,
        'cart': cart,
    })


@login_required
def cart_update(request, product_id):
    if request.method != 'POST':
        return redirect('carrito')

    producto = get_object_or_404(VarianteProducto, pk=product_id, activo=True)
    try:
        qty = int(request.POST.get('cantidad', '1'))
    except ValueError:
        qty = 1

    qty = max(1, min(qty, 10))

    saldo = SaldoInventario.objects.filter(variante=producto).first()
    disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0)) if saldo else 0
    if qty > disponible:
        messages.error(request, 'No hay stock suficiente para esa cantidad.')
        return redirect('carrito')

    cart = _get_cart(request.session)
    cart[str(product_id)] = qty
    _save_cart(request.session, cart)
    messages.success(request, 'Cantidad actualizada.')
    return redirect('carrito')


@login_required
def cart_remove(request, product_id):
    cart = _get_cart(request.session)
    if str(product_id) in cart:
        del cart[str(product_id)]
        _save_cart(request.session, cart)
        messages.info(request, 'Producto eliminado del carrito.')
    return redirect('carrito')


@login_required
def checkout_view(request):
    cart = _get_cart(request.session)
    if not cart:
        messages.error(request, 'Tu carrito está vacío.')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return JsonResponse({'ok': False, 'error': 'Tu carrito está vacío.'}, status=400)
        return redirect('carrito')

    variantes = (
        VarianteProducto.objects
        .filter(id_variante__in=[int(pid) for pid in cart.keys()], activo=True)
        .select_related('producto')
    )
    map_prod = {v.id_variante: v for v in variantes}

    items = []
    total = Decimal('0')
    direccion_prefill = _get_user_shipping_address(request.user)

    for pid, qty in cart.items():
        prod = map_prod.get(int(pid))
        if not prod:
            continue
        qty_int = int(qty)
        subtotal = Decimal(prod.precio) * qty_int
        total += subtotal
        items.append({
            'producto': prod.producto,
            'variante': prod,
            'cantidad': qty_int,
            'subtotal': subtotal,
            'precio_unitario': prod.precio,
        })

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        from .forms import CheckoutForm
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            error_msg = next(iter(form.errors.values()))[0]
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('checkout')

        metodo = form.cleaned_data['metodo_pago']
        direccion_linea1 = form.cleaned_data['linea1']
        direccion_linea2 = form.cleaned_data['linea2']
        ciudad = form.cleaned_data['ciudad']
        departamento = form.cleaned_data['departamento']
        nombre_destinatario = f"{request.user.nombre} {request.user.apellido}".strip() or request.user.correo
        codigo_postal = ''

        if metodo == 'tarjeta':
            card_error = _validate_card_payment_payload(request.POST)
            if card_error:
                if is_ajax:
                    return JsonResponse({'ok': False, 'error': card_error}, status=400)
                messages.error(request, card_error)
                return redirect('checkout')

        try:
            direccion_data = {
                'linea1': direccion_linea1,
                'linea2': direccion_linea2,
                'ciudad': ciudad,
                'departamento': departamento,
                'codigo_postal': codigo_postal,
                'nombre_destinatario': nombre_destinatario,
            }
            pedido = create_pedido_from_cart(request.user, items, direccion_data, metodo)
            create_transaccion(pedido, metodo, request.user)
            
            if metodo.lower() == 'contraentrega':
                from .services import descontar_stock_pedido
                descontar_stock_pedido(pedido, request.user)
                
        except ValidationError as exc:
            error_msg = '; '.join(v[0] for v in exc.message_dict.values()) if hasattr(exc, 'message_dict') else str(exc)
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('carrito')

        _sync_user_shipping_address(request.user, {
            'linea1': direccion_linea1,
            'linea2': direccion_linea2,
            'ciudad': ciudad,
            'departamento': departamento,
            'codigo_postal': codigo_postal,
            'nombre_destinatario': nombre_destinatario,
        })

        _save_cart(request.session, {})
        if is_ajax:
            factura_url = request.build_absolute_uri(reverse('factura', kwargs={'pedido_id': pedido.id_pedido}))
            return JsonResponse({'ok': True, 'factura_url': factura_url})
        messages.success(request, 'Pedido creado con éxito.')
        return redirect('factura', pedido_id=pedido.id_pedido)

    return render(request, 'checkout.html', {
        'items': items,
        'total': total,
        'cart': cart,
        'direccion_prefill': direccion_prefill,
    })


@login_required
def invoice_view(request, pedido_id):
    pedido = get_object_or_404(PedidoVenta, pk=pedido_id, cliente__usuario=request.user)
    cart = _get_cart(request.session)
    return render(request, 'factura.html', {'pedido': pedido, 'cart': cart})


@login_required
def invoice_pdf_view(request, pedido_id):
    pedido = get_object_or_404(PedidoVenta, pk=pedido_id, cliente__usuario=request.user)
    html_string = render_to_string('factura_pdf.html', {'pedido': pedido, 'request': request})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{pedido.id_pedido}.pdf"'
    return response


@admin_required
def detalle_pedido(request, id):
    pedido = get_object_or_404(
        PedidoVenta.objects
        .select_related('cliente__usuario', 'direccion_envio')
        .prefetch_related(
            'detalles__variante__producto',
            'historial_estados__cambiado_por',
            'transacciones__proveedor',
        ),
        id_pedido=id,
    )
    return render(request, 'pedidos/detalle.html', {'pedido': pedido})