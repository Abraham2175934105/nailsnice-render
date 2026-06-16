from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    action = models.CharField(max_length=100)
    model = models.CharField(max_length=120, blank=True, default='')
    object_id = models.CharField(max_length=120, blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.model}#{self.object_id}"


# ==============================================================================
# VISTAS DE BUSINESS INTELLIGENCE (OBJETIVO 7 - JUAN HERNÁNDEZ)
# Modelos Unmanaged acoplados a la estructura relacional 3FN de la base de datos.
# ==============================================================================

class VWVentasDiarias(models.Model):
    """
    Mapea la vista analítica de ventas diarias agregadas.
    """
    fecha_venta = models.DateField(primary_key=True)
    cantidad_pedidos = models.BigIntegerField()
    ingresos_brutos = models.DecimalField(max_digits=12, decimal_places=2)
    ticket_promedio = models.DecimalField(max_digits=12, decimal_places=2)
    puntos_generados = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def fecha(self):
        """Mantiene compatibilidad con llamadas estándar de fecha."""
        return self.fecha_venta

    @property
    def total_ventas(self):
        """Alias para ingresos brutos requeridos por el Dashboard."""
        return self.ingresos_brutos

    class Meta:
        managed = False
        db_table = 'vw_ventas_diarias'
        verbose_name = 'Venta Diaria (BI)'
        verbose_name_plural = 'Ventas Diarias (BI)'


class VWProductosTopMensual(models.Model):
    """
    Mapea la vista de los productos más vendidos del mes en curso.
    """
    id_producto = models.BigIntegerField(primary_key=True)
    periodo_ym = models.CharField(max_length=7)
    nombre_producto = models.CharField(max_length=255)
    unidades_vendidas = models.BigIntegerField()
    ingresos = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'vw_productos_top_mensual'
        verbose_name = 'Producto Top Mensual (BI)'
        verbose_name_plural = 'Productos Top Mensual (BI)'


class VWSaludInventario(models.Model):
    """
    Mapea el estado crítico, existencias y alertas de reorden del inventario.
    """
    id_variante = models.BigIntegerField(primary_key=True)
    id_bodega = models.BigIntegerField()
    codigo_bodega = models.CharField(max_length=64)
    nombre_bodega = models.CharField(max_length=255)
    id_producto = models.BigIntegerField()
    nombre_producto = models.CharField(max_length=255)
    sku = models.CharField(max_length=128)
    cantidad_existencia = models.IntegerField()
    cantidad_reservada = models.IntegerField()
    cantidad_disponible = models.IntegerField()
    nivel_reorden = models.IntegerField(null=True)
    alerta_reorden = models.IntegerField()

    @property
    def producto_nombre(self):
        return self.nombre_producto

    @property
    def stock_actual(self):
        return self.cantidad_disponible

    class Meta:
        managed = False
        db_table = 'vw_salud_inventario'
        verbose_name = 'Salud de Inventario (BI)'
        verbose_name_plural = 'Salud de Inventario (BI)'


class VWAgendamientosDiarios(models.Model):
    """
    Mapea la programación y los estados de citas y servicios para el día.
    """
    fecha_agendamiento = models.DateField(primary_key=True)
    total_agendamientos = models.BigIntegerField()
    completados = models.BigIntegerField()
    cancelados = models.BigIntegerField()
    no_asistieron = models.BigIntegerField()
    duracion_promedio_minutos = models.FloatField(null=True)

    @property
    def fecha_cita(self):
        return self.fecha_agendamiento

    class Meta:
        managed = False
        db_table = 'vw_agendamientos_diarios'
        verbose_name = 'Agendamiento Diario (BI)'
        verbose_name_plural = 'Agendamientos Diarios (BI)'


class VWValorCliente(models.Model):
    """
    Mapea el valor de ciclo de vida del cliente (CLV) y sus segmentaciones.
    """
    id_usuario_cliente = models.BigIntegerField(primary_key=True)
    correo = models.CharField(max_length=255)
    nombre_cliente = models.CharField(max_length=512)
    total_pedidos = models.BigIntegerField()
    valor_vida = models.DecimalField(max_digits=14, decimal_places=2)
    valor_promedio_pedido = models.DecimalField(max_digits=14, decimal_places=2)
    ultimo_pedido_en = models.DateTimeField(null=True)
    puntos_actuales = models.IntegerField(null=True)

    @property
    def cliente_nombre(self):
        return self.nombre_cliente

    @property
    def total_comprado(self):
        return self.valor_vida

    class Meta:
        managed = False
        db_table = 'vw_valor_cliente'
        verbose_name = 'Valor de Cliente (BI)'
        verbose_name_plural = 'Valor de Clientes (BI)'