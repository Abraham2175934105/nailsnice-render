from django.conf import settings
from django.core.exceptions import FieldError
from django.db import transaction

from core.audit import record_audit
from productos.models import Producto
from .models import (
    ProductoMaquillaje,
    MovimientoInventario,
    ItemMovimientoInventario,
    SaldoInventario,
    TipoMovimientoInventario,
    Bodega,
)


def _sync_catalogo(producto_inv: ProductoMaquillaje, user=None):
    estado = 'Activo' if producto_inv.is_active and producto_inv.estado == 'disponible' else 'Inactivo'
    imagen_value = None
    if producto_inv.imagen:
        imagen_value = (getattr(producto_inv.imagen, 'name', '') or '').strip()
        media_prefix = (settings.MEDIA_URL or '/media/').lstrip('/')
        if media_prefix and imagen_value.startswith(media_prefix):
            imagen_value = imagen_value[len(media_prefix):].lstrip('/')
        imagen_value = imagen_value.lstrip('/') or None

    defaults = {
        'nombre': producto_inv.nombre,
        'descripcion': producto_inv.descripcion or producto_inv.nombre,
        'precio': producto_inv.precio,
        'estado_producto': estado,
        'imagen': imagen_value,
    }
    try:
        producto, created = Producto.objects.get_or_create(inventario=producto_inv, defaults=defaults)
    except FieldError:
        return None
    changed = {}
    for field, value in defaults.items():
        if getattr(producto, field) != value:
            changed[field] = {'old': getattr(producto, field), 'new': value}
            setattr(producto, field, value)
    if changed:
        producto.save(update_fields=list(defaults.keys()))
        record_audit('productos.sync.update', user, 'Producto', producto.pk, {'changes': changed})
    elif created:
        record_audit('productos.sync.create', user, 'Producto', producto.pk, {'defaults': defaults})
    return producto


def save_producto_form(form, user=None):
    with transaction.atomic():
        is_new = form.instance.pk is None
        producto = form.save()
        changes = {field: form.cleaned_data.get(field) for field in form.changed_data}
        record_audit(
            f"inventario.{'create' if is_new else 'update'}",
            user,
            'ProductoMaquillaje',
            producto.id_inventario,
            {'changes': changes},
        )
        _sync_catalogo(producto, user=user)
        return producto


def soft_delete_producto(producto: ProductoMaquillaje, user=None):
    if not producto.is_active:
        return producto
    producto.is_active = False
    producto.save(update_fields=['is_active'])
    record_audit('inventario.soft_delete', user, 'ProductoMaquillaje', producto.id_inventario, {'is_active': False})
    try:
        prod = Producto.objects.filter(inventario=producto).first()
        if prod:
            prod.estado_producto = 'Inactivo'
            prod.save(update_fields=['estado_producto'])
            record_audit('productos.sync.deactivate', user, 'Producto', prod.pk, {'estado_producto': 'Inactivo'})
    except Exception:
        pass
    return producto


def registrar_movimiento(tipo_movimiento_id, bodega_id, items, notas=None, user=None):
    """
    Crea un MovimientoInventario con sus items y actualiza SaldoInventario.
    items = [{'variante_id': X, 'cantidad': N, 'costo_unitario': C}]
    """
    with transaction.atomic():
        tipo = TipoMovimientoInventario.objects.get(pk=tipo_movimiento_id)
        bodega = Bodega.objects.get(pk=bodega_id)

        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento=tipo,
            bodega=bodega,
            notas=notas,
            creado_por=user,
        )

        for item in items:
            variante_id = item['variante_id']
            cantidad = item['cantidad']
            costo_unitario = item.get('costo_unitario')

            ItemMovimientoInventario.objects.create(
                movimiento=movimiento,
                variante_id=variante_id,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
            )

            saldo, _ = SaldoInventario.objects.get_or_create(
                variante_id=variante_id,
                defaults={'bodega': bodega, 'cantidad_existencia': 0},
            )

            if tipo.direccion == 1:
                saldo.cantidad_existencia += cantidad
            elif tipo.direccion == -1:
                saldo.cantidad_existencia = max(0, saldo.cantidad_existencia - cantidad)

            saldo.save(update_fields=['cantidad_existencia', 'actualizado_en'])

        record_audit('inventario.movimiento.create', user, 'MovimientoInventario', movimiento.pk, {
            'tipo': tipo.codigo,
            'bodega': bodega.nombre,
            'items': items,
        })

        return movimiento


def obtener_salud_inventario(bodega_id=None):
    """
    Devuelve saldos con flag alerta_reorden=True/False.
    Replica la vista SQL vw_salud_inventario.
    """
    qs = SaldoInventario.objects.select_related('variante', 'bodega')

    if bodega_id:
        qs = qs.filter(bodega_id=bodega_id)

    resultado = []
    for saldo in qs:
        disponible = saldo.cantidad_existencia - saldo.cantidad_reservada
        alerta_reorden = disponible <= saldo.nivel_reorden
        resultado.append({
            'variante_id': saldo.variante_id,
            'variante': str(saldo.variante),
            'bodega': str(saldo.bodega),
            'cantidad_existencia': saldo.cantidad_existencia,
            'cantidad_reservada': saldo.cantidad_reservada,
            'disponible': disponible,
            'nivel_reorden': saldo.nivel_reorden,
            'alerta_reorden': alerta_reorden,
        })

    return resultado