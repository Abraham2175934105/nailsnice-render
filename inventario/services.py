from django.db import transaction
from django.conf import settings

from core.audit import record_audit
from productos.models import Producto
from .models import ProductoMaquillaje


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
    producto, created = Producto.objects.get_or_create(inventario=producto_inv, defaults=defaults)
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
