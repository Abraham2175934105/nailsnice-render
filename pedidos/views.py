from decimal import Decimal
import io
import re

import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML

from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from clientes.models import Cliente
from inventario.models import ProductoMaquillaje
from web.models import Clientes as LegacyClientes
from .forms import PedidosForm
from .models import Pedidos, Pedido, DetallePedido
from .services import create_pedido_from_cart, delete_legacy_pedido, save_legacy_pedido

PEDIDOS_COLUMNS = [
    ('id', 'ID'),
    ('usuario', 'Usuario'),
    ('telefono', 'Teléfono'),
    ('producto', 'Producto'),
    ('precio', 'Precio'),
    ('direccion', 'Dirección'),
    ('cantidad', 'Cantidad'),
    ('fecha', 'Fecha'),
]
PEDIDOS_DEFAULT_COLUMNS = ['id', 'usuario', 'producto', 'precio', 'cantidad', 'fecha']
PAGE_MIN = 10
PAGE_MAX = 30
DIRECCION_COLOMBIA_RE = re.compile(r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+')


def _is_valid_colombian_address(address: str) -> bool:
    return bool(DIRECCION_COLOMBIA_RE.match((address or '').strip()))


def _get_user_shipping_address(user) -> str:
    try:
        cliente = user.cliente
        direccion_cliente = (cliente.direccion or '').strip()
        if direccion_cliente:
            return direccion_cliente
    except (ObjectDoesNotExist, Cliente.DoesNotExist, AttributeError):
        pass

    legacy_cliente = LegacyClientes.objects.filter(correo__iexact=getattr(user, 'email', '')).first()
    if legacy_cliente:
        direccion_legacy = (legacy_cliente.direccion or '').strip()
        if direccion_legacy:
            return direccion_legacy

    ultimo_pedido = Pedido.objects.filter(usuario=user).order_by('-creado_en').first()
    if ultimo_pedido:
        direccion_pedido = (ultimo_pedido.direccion_envio or '').strip()
        if direccion_pedido:
            return direccion_pedido

    ultimo_legacy_pedido = Pedidos.activos.filter(usuario__iexact=getattr(user, 'email', '')).order_by('-fecha', '-id').first()
    if ultimo_legacy_pedido:
        direccion_legacy_pedido = (ultimo_legacy_pedido.direccion or '').strip()
        if direccion_legacy_pedido:
            return direccion_legacy_pedido
    return ''


def _sync_user_shipping_address(user, direccion: str):
    direccion_limpia = (direccion or '').strip()
    if not direccion_limpia:
        return

    try:
        cliente = user.cliente
        if (cliente.direccion or '').strip() != direccion_limpia:
            cliente.direccion = direccion_limpia
            cliente.save(update_fields=['direccion'])
    except (ObjectDoesNotExist, Cliente.DoesNotExist, AttributeError):
        Cliente.objects.update_or_create(
            usuario=user,
            defaults={'direccion': direccion_limpia},
        )

    legacy_cliente = LegacyClientes.objects.filter(correo__iexact=user.email).first()
    if legacy_cliente:
        if (legacy_cliente.direccion or '').strip() != direccion_limpia:
            legacy_cliente.direccion = direccion_limpia
            legacy_cliente.save(update_fields=['direccion'])
    else:
        LegacyClientes.objects.create(
            nombre=(getattr(user, 'nombre1', '') or 'Cliente')[:100],
            apellido=(getattr(user, 'apellido1', '') or 'NailsNice')[:100],
            direccion=direccion_limpia[:100],
            telefono=(getattr(user, 'telefono', '') or '0000000000')[:100],
            correo=(getattr(user, 'email', '') or '')[:100],
        )

def inicio(request):
    return render(request, 'pedidos/index.html')


def _build_pedidos_rows(queryset, selected):
    config = {
        'id': ('ID', lambda p: p.id),
        'usuario': ('Usuario', lambda p: p.usuario),
        'telefono': ('Teléfono', lambda p: p.telefono),
        'producto': ('Producto', lambda p: p.producto),
        'precio': ('Precio', lambda p: p.precio),
        'direccion': ('Dirección', lambda p: p.direccion),
        'cantidad': ('Cantidad', lambda p: p.cantidad),
        'fecha': ('Fecha', lambda p: p.fecha),
    }
    keys = [k for k in selected if k in config] or ['id', 'usuario', 'producto', 'precio', 'cantidad', 'fecha']
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
    pedidos_qs = Pedidos.activos.all().order_by('-fecha', '-id')
    search = (request.GET.get('q') or '').strip()
    if search:
        pedidos_qs = pedidos_qs.filter(
            Q(usuario__icontains=search) |
            Q(producto__icontains=search) |
            Q(direccion__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(pedidos_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(PEDIDOS_COLUMNS)] or PEDIDOS_DEFAULT_COLUMNS
    export_scope = (request.GET.get('export_scope') or 'page').lower()
    export_page = request.GET.get('export_page') or page_obj.number

    export_fmt = (request.GET.get('export') or '').lower()
    if export_fmt in {'csv', 'xlsx', 'pdf'}:
        export_source = pedidos_qs if export_scope == 'all' else paginator.get_page(export_page).object_list
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
    })

@admin_required
def crear_pedido(request):
    if request.method == 'POST':
        form = PedidosForm(request.POST)
        if form.is_valid():
            save_legacy_pedido(form, user=request.user)
            return redirect('lista_pedidos')
    else:
        form = PedidosForm()
    return render(request, 'pedidos/formulario.html', {'form': form})

@admin_required
def editar_pedido(request, id):
    pedido = get_object_or_404(Pedidos, id=id, is_active=True)
    if request.method == 'POST':
        form = PedidosForm(request.POST, instance=pedido)
        if form.is_valid():
            save_legacy_pedido(form, user=request.user)
            return redirect('lista_pedidos')
    else:
        form = PedidosForm(instance=pedido)
    return render(request, 'pedidos/formulario.html', {'form': form})

@admin_required
def eliminar_pedido(request, id):
    pedido = get_object_or_404(Pedidos, id=id, is_active=True)  # ← minúscula
    delete_legacy_pedido(pedido, user=request.user)
    return redirect('lista_pedidos')


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

    producto = get_object_or_404(ProductoMaquillaje.activos, pk=product_id)
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

    if new_qty > producto.stock:
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
        productos = ProductoMaquillaje.activos.filter(id_inventario__in=[int(pid) for pid in cart.keys()])
        map_prod = {p.id_inventario: p for p in productos}
        for pid, qty in list(cart.items()):
            prod = map_prod.get(int(pid))
            if not prod:
                cart.pop(str(pid), None)
                cart_changed = True
                continue

            qty_int = int(qty)
            if prod.stock <= 0:
                cart.pop(str(pid), None)
                cart_changed = True
                continue
            if qty_int > prod.stock:
                qty_int = prod.stock
                cart[str(pid)] = qty_int
                cart_changed = True

            subtotal = Decimal(prod.precio) * qty_int
            total += subtotal
            items.append({
                'producto': prod,
                'cantidad': qty_int,
                'subtotal': subtotal,
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

    producto = get_object_or_404(ProductoMaquillaje.activos, pk=product_id)
    try:
        qty = int(request.POST.get('cantidad', '1'))
    except ValueError:
        qty = 1

    qty = max(1, min(qty, 10))

    if qty > producto.stock:
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

    productos = ProductoMaquillaje.activos.filter(id_inventario__in=[int(pid) for pid in cart.keys()])
    map_prod = {p.id_inventario: p for p in productos}

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
        items.append({'producto': prod, 'cantidad': qty_int, 'subtotal': subtotal})

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        metodo = request.POST.get('metodo_pago')
        direccion = (request.POST.get('direccion') or '').strip()

        if not direccion and direccion_prefill:
            direccion = direccion_prefill

        if metodo not in ['contraentrega', 'tarjeta']:
            error_msg = 'Selecciona un método de pago.'
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('checkout')
        if not direccion:
            error_msg = 'La dirección de envío es obligatoria.'
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('checkout')
        if not _is_valid_colombian_address(direccion):
            error_msg = 'La dirección debe tener un formato de vía colombiano (ej: "Calle 123 #45-67").'
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('checkout')

        try:
            pedido = create_pedido_from_cart(request.user, items, direccion, metodo)
        except ValidationError as exc:
            error_msg = '; '.join(v[0] for v in exc.message_dict.values()) if hasattr(exc, 'message_dict') else str(exc)
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('carrito')

        _sync_user_shipping_address(request.user, direccion)

        _save_cart(request.session, {})
        if is_ajax:
            factura_url = request.build_absolute_uri(reverse('factura', kwargs={'pedido_id': pedido.id}))
            return JsonResponse({'ok': True, 'factura_url': factura_url})
        messages.success(request, 'Pedido creado con éxito.')
        return redirect('factura', pedido_id=pedido.id)

    return render(request, 'checkout.html', {
        'items': items,
        'total': total,
        'cart': cart,
        'direccion_prefill': direccion_prefill,
    })


@login_required
def invoice_view(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, usuario=request.user)
    cart = _get_cart(request.session)
    return render(request, 'factura.html', {'pedido': pedido, 'cart': cart})


@login_required
def invoice_pdf_view(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, usuario=request.user)
    html_string = render_to_string('factura_pdf.html', {'pedido': pedido, 'request': request})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{pedido.id}.pdf"'
    return response