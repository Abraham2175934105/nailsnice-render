from django.conf import settings
from django.db import models


class Cliente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        db_column='id_usuario',
        on_delete=models.CASCADE,
        related_name='perfil_cliente',
    )
    acepta_fidelizacion = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'perfil_cliente'
        managed = True
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['usuario__correo']

    def __str__(self):
        return f"Cliente: {self.usuario.correo}"

    def delete(self, using=None, keep_parents=False):
        usuario = self.usuario
        # CORRECCIÓN: Se captura el retorno original (tuple) para no romper la firma del método
        deleted_stats = super().delete(using=using, keep_parents=keep_parents)
        usuario.delete()
        return deleted_stats


class DireccionUsuario(models.Model):
    # Valores válidos según CHECK en la BD
    TIPO_ENVIO = 'ENVIO'
    TIPO_FACTURA = 'FACTURA'
    TIPO_OTRA = 'OTRA'
    TIPO_CHOICES = [
        (TIPO_ENVIO, 'Envío'),
        (TIPO_FACTURA, 'Factura'),
        (TIPO_OTRA, 'Otra'),
    ]

    id_direccion = models.BigAutoField(primary_key=True, db_column='id_direccion')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='id_usuario',
        on_delete=models.CASCADE,
        related_name='direcciones',
    )
    tipo_direccion = models.CharField(max_length=20, choices=TIPO_CHOICES)  # CHECK en BD
    etiqueta = models.CharField(max_length=60, null=True, blank=True)
    nombre_destinatario = models.CharField(max_length=120)
    linea1 = models.CharField(max_length=160)
    linea2 = models.CharField(max_length=160, null=True, blank=True)
    ciudad = models.CharField(max_length=80)
    departamento = models.CharField(max_length=80, null=True, blank=True)
    codigo_postal = models.CharField(max_length=20, null=True, blank=True)
    codigo_pais = models.CharField(max_length=2, default='CO')
    es_predeterminada_envio = models.BooleanField(default=False)
    es_predeterminada_factura = models.BooleanField(default=False)
    # Columnas GENERATED ALWAYS AS en MySQL — Django no las escribe, solo las lee
    id_usuario_envio_predeterminado = models.BigIntegerField(
        null=True,
        editable=False,
        db_column='id_usuario_envio_predeterminado',
    )
    id_usuario_factura_predeterminado = models.BigIntegerField(
        null=True,
        editable=False,
        db_column='id_usuario_factura_predeterminado',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'direccion_usuario'
        managed = True
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['usuario', 'es_predeterminada_envio']),
            models.Index(fields=['usuario', 'es_predeterminada_factura']),
        ]

    def __str__(self):
        # CORRECCIÓN: Acceso seguro a la PK del usuario relacionado para el linter
        return f"{self.usuario.pk} - {self.linea1}"


class ProveedorPago(models.Model):
    id_proveedor = models.BigAutoField(primary_key=True, db_column='id_proveedor')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'proveedor_pago'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class TipoMetodoPago(models.Model):
    id_tipo_metodo = models.BigAutoField(primary_key=True, db_column='id_tipo_metodo')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=80, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipo_metodo_pago'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MetodoPagoCliente(models.Model):
    # Valores válidos según CHECK en la BD
    ESTADO_ACTIVO = 'ACTIVO'
    ESTADO_INACTIVO = 'INACTIVO'
    ESTADO_REVOCADO = 'REVOCADO'
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, 'Activo'),
        (ESTADO_INACTIVO, 'Inactivo'),
        (ESTADO_REVOCADO, 'Revocado'),
    ]

    id_metodo_pago = models.BigAutoField(primary_key=True, db_column='id_metodo_pago')
    cliente = models.ForeignKey(
        Cliente,
        db_column='id_usuario_cliente',
        on_delete=models.CASCADE,
        related_name='metodos_pago',
    )
    tipo_metodo = models.ForeignKey(
        TipoMetodoPago,
        db_column='id_tipo_metodo',
        on_delete=models.RESTRICT,
        related_name='metodos_cliente',
    )
    proveedor = models.ForeignKey(
        ProveedorPago,
        db_column='id_proveedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metodos_cliente',
    )
    token = models.CharField(max_length=255)
    etiqueta_mascara = models.CharField(max_length=80)
    nombre_titular = models.CharField(max_length=120, null=True, blank=True)
    ultimos4 = models.CharField(max_length=4, null=True, blank=True)
    mes_expiracion = models.PositiveSmallIntegerField(null=True, blank=True)  # CHECK 1-12 en BD
    anio_expiracion = models.PositiveSmallIntegerField(null=True, blank=True)
    es_predeterminado = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)  # CHECK en BD
    # Columna GENERATED ALWAYS AS en MySQL — Django no la escribe, solo las lee
    id_propietario_predeterminado = models.BigIntegerField(
        null=True,
        editable=False,
        db_column='id_propietario_predeterminado',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'metodo_pago_cliente'
        managed = True
        ordering = ['-creado_en']

    def __str__(self):
        # CORRECCIÓN: Acceso seguro a la PK de la relación cliente
        return f"{self.cliente.pk} - {self.etiqueta_mascara}"


class ConfiguracionFidelizacion(models.Model):
    id_config = models.PositiveSmallIntegerField(primary_key=True, db_column='id_config')
    monto_base = models.DecimalField(max_digits=12, decimal_places=2)
    puntos_por_unidad = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'configuracion_fidelizacion'
        managed = True

    def __str__(self):
        return f"Config fidelización #{self.id_config}"


class CuentaFidelizacion(models.Model):
    cliente = models.OneToOneField(
        Cliente,
        primary_key=True,
        db_column='id_usuario_cliente',
        on_delete=models.CASCADE,
        related_name='cuenta_fidelizacion',
    )
    puntos_actuales = models.IntegerField(default=0)       # INT (puede ser negativo en tránsito)
    total_ganados = models.PositiveIntegerField(default=0)
    total_redimidos = models.PositiveIntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'cuenta_fidelizacion'
        managed = True

    def __str__(self):
        # CORRECCIÓN: Acceso a través del atributo PK del cliente relacionado
        return f"Fidelización cliente {self.cliente.pk}"


class LibroPuntos(models.Model):
    # Valores válidos según CHECK en la BD
    ORIGEN_ORDEN_GANA = 'ORDEN_GANA'
    ORIGEN_ORDEN_REDIME = 'ORDEN_REDIME'
    ORIGEN_AJUSTE_MANUAL = 'AJUSTE_MANUAL'
    ORIGEN_EXPIRACION = 'EXPIRACION'
    TIPO_ORIGEN_CHOICES = [
        (ORIGEN_ORDEN_GANA, 'Orden gana puntos'),
        (ORIGEN_ORDEN_REDIME, 'Orden redime puntos'),
        (ORIGEN_AJUSTE_MANUAL, 'Ajuste manual'),
        (ORIGEN_EXPIRACION, 'Expiración'),
    ]

    id_movimiento_puntos = models.BigAutoField(
        primary_key=True, db_column='id_movimiento_puntos'
    )
    cliente = models.ForeignKey(
        Cliente,
        db_column='id_usuario_cliente',
        on_delete=models.RESTRICT,       # RESTRICT en BD: no borrar cliente con movimientos
        related_name='movimientos_puntos',
    )
    pedido_id = models.BigIntegerField(null=True, blank=True, db_column='id_pedido')
    tipo_origen = models.CharField(max_length=20, choices=TIPO_ORIGEN_CHOICES)  # CHECK en BD
    puntos_delta = models.IntegerField()   # positivo = ganó, negativo = redimió/expiró
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='creado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movimientos_puntos_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'libro_puntos'
        managed = True
        ordering = ['-creado_en']

    def __str__(self):
        return f"Mov {self.id_movimiento_puntos} — {self.tipo_origen} ({self.puntos_delta:+d} pts)"