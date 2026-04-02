from django.db import migrations
from django.utils import timezone


def link_productos_to_inventario(apps, schema_editor):
    Producto = apps.get_model('productos', 'Producto')
    ProductoMaquillaje = apps.get_model('inventario', 'ProductoMaquillaje')

    for prod in Producto.objects.all():
        if getattr(prod, 'inventario_id', None):
            continue

        inv_obj = None

        # 1) Match by case-insensitive name
        name = (prod.nombre or '').strip()
        if name:
            qs = ProductoMaquillaje.objects.filter(nombre__iexact=name).order_by('id_inventario')
            inv_obj = qs.first()

        # 2) Fallback: match by id equality (common in some dumps)
        if not inv_obj:
            try:
                inv_obj = ProductoMaquillaje.objects.get(id_inventario=prod.id)
            except ProductoMaquillaje.DoesNotExist:
                inv_obj = None

        # 3) Create inventory entry if not found
        if not inv_obj:
            marca = ''
            if getattr(prod, 'id_marca_id', None):
                marca_rel = getattr(prod, 'id_marca', None)
                if marca_rel:
                    marca = getattr(marca_rel, 'nombre_marca', '') or ''
            inv_obj = ProductoMaquillaje.objects.create(
                nombre=name or f"Producto {prod.id}",
                cantidad=0,
                estado='disponible',
                fecha_ingreso=timezone.now().date(),
                stock=0,
                precio=prod.precio,
                descripcion=(prod.descripcion or '')[:255],
                marca=marca or 'Sin marca',
                imagen=prod.imagen or None,
            )

        prod.inventario = inv_obj
        prod.save(update_fields=['inventario'])


def unlink(apps, schema_editor):
    # No-op rollback (field removal handled by migration history if reversed)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0003_producto_inventario'),
    ]

    operations = [
        migrations.RunPython(link_productos_to_inventario, unlink),
    ]
