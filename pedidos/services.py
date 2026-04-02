from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.audit import record_audit
from .models import DetallePedido, Pedido, Pedidos


def save_legacy_pedido(form, user=None):
    with transaction.atomic():
        is_new = form.instance.pk is None
        pedido = form.save()
        changes = {field: form.cleaned_data.get(field) for field in form.changed_data}
        record_audit(
            f"pedidos.legacy.{'create' if is_new else 'update'}",
            user,
            'Pedidos',
            pedido.pk,
            {'changes': changes},
        )
        return pedido


def delete_legacy_pedido(pedido: Pedidos, user=None):
    if not pedido.is_active:
        return pedido
    pedido.is_active = False
    pedido.save(update_fields=['is_active'])
    record_audit('pedidos.legacy.delete', user, 'Pedidos', pedido.pk, {'is_active': False})
    return pedido


def _build_audit_items(items):
    return [
        {'producto': item['producto'].id_inventario, 'cantidad': item['cantidad']}
        for item in items
    ]


def _sync_legacy_pedidos(usuario, items, direccion: str):
    legacy_rows = []
    fecha_hoy = timezone.now().date()
    telefono = str(getattr(usuario, 'telefono', '') or '').strip()
    usuario_ref = str(getattr(usuario, 'email', '') or '').strip()
    direccion_ref = str(direccion or '').strip()[:100]

    for item in items:
        producto = item['producto']
        cantidad = int(item['cantidad'])
        subtotal = Decimal(producto.precio) * cantidad
        legacy_rows.append(
            Pedidos(
                usuario=usuario_ref[:100],
                telefono=telefono[:100],
                producto=str(producto.nombre or '')[:100],
                precio=subtotal,
                direccion=direccion_ref,
                cantidad=cantidad,
                fecha=fecha_hoy,
                is_active=True,
            )
        )

    if legacy_rows:
        Pedidos.objects.bulk_create(legacy_rows)


def create_pedido_from_cart(usuario, items, direccion: str, metodo: str) -> Pedido:
    if not items:
        raise ValidationError({'items': 'No hay items en el carrito.'})

    total = Decimal('0')
    for item in items:
        producto = item['producto']
        cantidad = int(item['cantidad'])
        if not producto.is_active:
            raise ValidationError({'producto': f"El producto {producto.nombre} está inactivo."})
        if cantidad > producto.stock:
            raise ValidationError({'stock': f"Stock insuficiente para {producto.nombre}."})
        total += Decimal(producto.precio) * cantidad

    with transaction.atomic():
        pedido = Pedido.objects.create(
            usuario=usuario,
            direccion_envio=direccion,
            metodo_pago=metodo,
            estado='pendiente',
            total=total,
        )

        for item in items:
            producto = item['producto']
            cantidad = int(item['cantidad'])
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=producto.precio,
            )
            producto.stock = max(0, producto.stock - cantidad)
            producto.save(update_fields=['stock'])

        _sync_legacy_pedidos(usuario, items, direccion)

        record_audit(
            'pedidos.create',
            usuario,
            'Pedido',
            pedido.pk,
            {
                'total': str(total),
                'items': _build_audit_items(items),
                'metodo': metodo,
            },
        )

    return pedido
