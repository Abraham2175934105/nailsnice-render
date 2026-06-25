from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Sum
from cloudinary.models import CloudinaryField


class Bodega(models.Model):
    id_bodega = models.BigAutoField(primary_key=True, db_column='id_bodega')
    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120, unique=True)
    ciudad = models.CharField(max_length=80, null=True, blank=True)
    codigo_pais = models.CharField(max_length=2, default='CO')
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bodega'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class TipoMovimientoInventario(models.Model):
    id_tipo_movimiento = models.PositiveSmallIntegerField(primary_key=True, db_column='id_tipo_movimiento')
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=160)
    direccion = models.SmallIntegerField()

    class Meta:
        db_table = 'tipo_movimiento_inventario'
        managed = True
        ordering = ['id_tipo_movimiento']

    def __str__(self):
        return self.codigo


class SaldoInventario(models.Model):
    # Composite PK in DB (id_bodega, id_variante); app assumes una bodega principal.
    variante = models.OneToOneField(
        'productos.VarianteProducto',
        primary_key=True,
        db_column='id_variante',
        on_delete=models.CASCADE,
        related_name='saldo_inventario',
    )
    bodega = models.ForeignKey(
        Bodega,
        db_column='id_bodega',
        on_delete=models.CASCADE,
        related_name='saldos',
    )
    cantidad_existencia = models.PositiveIntegerField(default=0)
    cantidad_reservada = models.PositiveIntegerField(default=0)
    nivel_reorden = models.PositiveIntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    # ==========================================================================
    # CAPA DE COMPATIBILIDAD DINÁMICA (Dashboard & Pylance Safe)
    # ==========================================================================
    @property
    def cantidad_disponible(self) -> int:
        """Calcula las existencias reales libres de reservas."""
        return max(0, self.cantidad_existencia - self.cantidad_reservada)

    @property
    def stock(self) -> int:
        """Alias para mapear el stock disponible de forma genérica."""
        return self.cantidad_disponible

    class Meta:
        db_table = 'saldo_inventario'
        managed = True
        indexes = [
            models.Index(fields=['bodega', 'actualizado_en']),
        ]


class MovimientoInventario(models.Model):
    id_movimiento = models.BigAutoField(primary_key=True, db_column='id_movimiento')
    tipo_movimiento = models.ForeignKey(
        TipoMovimientoInventario,
        db_column='id_tipo_movimiento',
        on_delete=models.RESTRICT,
        related_name='movimientos',
    )
    bodega = models.ForeignKey(
        Bodega,
        db_column='id_bodega',
        on_delete=models.RESTRICT,
        related_name='movimientos',
    )
    tipo_referencia = models.CharField(max_length=40, null=True, blank=True)
    id_referencia = models.CharField(max_length=80, null=True, blank=True)
    notas = models.CharField(max_length=255, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='creado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movimientos_inventario',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimiento_inventario'
        managed = True
        ordering = ['-creado_en']


class ItemMovimientoInventario(models.Model):
    id_item_movimiento = models.BigAutoField(primary_key=True, db_column='id_item_movimiento')
    movimiento = models.ForeignKey(
        MovimientoInventario,
        db_column='id_movimiento',
        on_delete=models.CASCADE,
        related_name='items',
    )
    variante = models.ForeignKey(
        'productos.VarianteProducto',
        db_column='id_variante',
        on_delete=models.RESTRICT,
        related_name='movimientos',
    )
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'item_movimiento_inventario'
        managed = True
        ordering = ['-creado_en']


# Compatibilidad con la versión histórica: algunos tests y servicios esperan
# un modelo llamado `ProductoMaquillaje`. Creamos un modelo sencillo que
# representa inventario de productos y mantiene un campo `id_inventario`
# utilizado por la lógica del proyecto.
class ProductoMaquillajeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ProductoMaquillaje(models.Model):
    id_inventario = models.BigAutoField(primary_key=True, db_column='id_inventario')
    nombre = models.CharField(max_length=160, db_index=True)
    cantidad = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=40, default='disponible')
    fecha_ingreso = models.DateField(null=True, blank=True)
    stock = models.IntegerField(default=0)
    # CORRECCIÓN SENIOR: Se cambia default=0 por Decimal('0.00') para corregir el tipado en Pylance
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descripcion = models.TextField(null=True, blank=True)
    marca = models.CharField(max_length=120, null=True, blank=True)
    proveedor = models.CharField(max_length=120, null=True, blank=True)
    color = models.CharField(max_length=80, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    imagen = CloudinaryField('imagen', folder='productos')
    creado_en = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    activos = ProductoMaquillajeManager()

    class Meta:
        db_table = 'producto_inventario'
        managed = True

    def __str__(self):
        return f"{self.nombre} ({self.id_inventario})"