from decimal import Decimal
from django.conf import settings
from django.db import models

from clientes.models import Cliente, DireccionUsuario, MetodoPagoCliente, ProveedorPago
from productos.models import VarianteProducto


class CarritoCompra(models.Model):
    id_carrito = models.BigAutoField(primary_key=True, db_column='id_carrito')
    cliente = models.ForeignKey(
        Cliente,
        db_column='id_usuario_cliente',
        on_delete=models.CASCADE,
        related_name='carritos',
    )
    estado = models.CharField(max_length=20, default='ACTIVO')
    id_cliente_activo = models.BigIntegerField(null=True, editable=False, db_column='id_cliente_activo')
    codigo_moneda = models.CharField(max_length=3, default='COP')
    expira_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'carrito_compra'
        managed = True
        ordering = ['-creado_en']

    def __str__(self):
        return f"Carrito {self.id_carrito}"


class ItemCarritoCompra(models.Model):
    id_item_carrito = models.BigAutoField(primary_key=True, db_column='id_item_carrito')
    carrito = models.ForeignKey(
        CarritoCompra,
        db_column='id_carrito',
        on_delete=models.CASCADE,
        related_name='items',
    )
    variante = models.ForeignKey(
        VarianteProducto,
        db_column='id_variante',
        on_delete=models.RESTRICT,
        related_name='items_carrito',
    )
    amount = models.PositiveIntegerField(default=1)  # alias por compatibilidad si se requiere
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'item_carrito_compra'
        managed = True
        ordering = ['-creado_en']


class PedidoVenta(models.Model):
    ESTADOS = [
        ('PENDIENTE_PAGO', 'Pendiente pago'),
        ('PAGADO', 'Pagado'),
        ('PROCESANDO', 'Procesando'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
        ('REEMBOLSADO', 'Reembolsado'),
    ]

    id_pedido = models.BigAutoField(primary_key=True, db_column='id_pedido')
    numero_pedido = models.CharField(max_length=30, blank=True, default='')
    cliente = models.ForeignKey(
        Cliente,
        db_column='id_usuario_cliente',
        on_delete=models.RESTRICT,
        related_name='pedidos',
    )
    carrito = models.ForeignKey(
        CarritoCompra,
        db_column='id_carrito',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pedidos',
    )
    estado = models.CharField(max_length=25, default='PENDIENTE_PAGO')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # CORRECCIONES SENIOR: Valores por defecto cambiados a objetos Decimal explícitos
    monto_envio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    monto_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    monto_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    puntos_ganados = models.PositiveIntegerField(default=0)
    puntos_redimidos = models.PositiveIntegerField(default=0)
    direccion_envio = models.ForeignKey(
        DireccionUsuario,
        db_column='id_direccion_envio',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pedidos_envio',
    )
    direccion_factura = models.ForeignKey(
        DireccionUsuario,
        db_column='id_direccion_factura',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pedidos_factura',
    )
    realizado_en = models.DateTimeField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'pedido_venta'
        managed = True
        ordering = ['-realizado_en']
        indexes = [
            models.Index(fields=['cliente', 'realizado_en']),
            models.Index(fields=['estado']),
            models.Index(fields=['numero_pedido']),
        ]

    def __str__(self):
        ref = self.numero_pedido or str(self.id_pedido)
        return f"Pedido {ref}"


class DetallePedidoVenta(models.Model):
    id_detalle_pedido = models.BigAutoField(primary_key=True, db_column='id_detalle_pedido')
    pedido = models.ForeignKey(
        PedidoVenta,
        db_column='id_pedido',
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    variante = models.ForeignKey(
        VarianteProducto,
        db_column='id_variante',
        on_delete=models.RESTRICT,
        related_name='detalles_pedido',
    )
    nombre_producto_snapshot = models.CharField(max_length=180)
    sku_snapshot = models.CharField(max_length=80)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    total_linea = models.DecimalField(max_digits=12, decimal_places=2, editable=False, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detalle_pedido_venta'
        managed = True
        ordering = ['-creado_en']

    def subtotal(self):
        return self.total_linea or (self.precio_unitario * self.cantidad)

    def __str__(self):
        return f"Detalle {self.id_detalle_pedido}"


class HistorialEstadoPedido(models.Model):
    id_historial_estado_pedido = models.BigAutoField(primary_key=True, db_column='id_historial_estado_pedido')
    pedido = models.ForeignKey(
        PedidoVenta,
        db_column='id_pedido',
        on_delete=models.CASCADE,
        related_name='historial_estados',
    )
    estado = models.CharField(max_length=25)
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='cambiado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cambios_estado_pedido',
    )
    nota = models.CharField(max_length=255, null=True, blank=True)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_estado_pedido'
        managed = True
        ordering = ['-cambiado_en']


class TransaccionPago(models.Model):
    id_transaccion = models.BigAutoField(primary_key=True, db_column='id_transaccion')
    pedido = models.ForeignKey(
        PedidoVenta,
        db_column='id_pedido',
        on_delete=models.CASCADE,
        related_name='transacciones',
    )
    metodo_pago = models.ForeignKey(
        MetodoPagoCliente,
        db_column='id_metodo_pago',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transacciones',
    )
    proveedor = models.ForeignKey(
        ProveedorPago,
        db_column='id_proveedor',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transacciones',
    )
    id_transaccion_proveedor = models.CharField(max_length=120, null=True, blank=True)
    estado = models.CharField(max_length=20)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_moneda = models.CharField(max_length=3, default='COP')
    motivo_falla = models.CharField(max_length=255, null=True, blank=True)
    respuesta_cruda_json = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')
    procesado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'transaccion_pago'
        managed = True
        ordering = ['-creado_en']