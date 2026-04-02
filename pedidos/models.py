from django.db import models
from django.conf import settings


# Modelo legado (se mantiene para compatibilidad; será reemplazado por Pedido/DetallePedido)
class ActivePedidosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Pedidos(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=100)
    telefono = models.CharField(max_length=100)
    producto = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    direccion = models.CharField(max_length=100)
    cantidad = models.IntegerField()
    fecha = models.DateField()
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    activos = ActivePedidosManager()

    def __str__(self):
        return self.usuario

    class Meta:
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['producto']),
            models.Index(fields=['direccion']),
            models.Index(fields=['fecha']),
        ]


class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pedidos')
    direccion_envio = models.CharField(max_length=255)
    metodo_pago = models.CharField(max_length=20, choices=[('contraentrega', 'Contraentrega'), ('tarjeta', 'Tarjeta')])
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.email}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('inventario.ProductoMaquillaje', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"Detalle #{self.id} - Pedido {self.pedido_id}"