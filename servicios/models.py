from django.conf import settings
from django.db import models

from clientes.models import Cliente
from usuarios.models import Empleado


class TipoServicio(models.Model):
    id_tipo_servicio = models.BigAutoField(primary_key=True, db_column='id_tipo_servicio')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipo_servicio'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CategoriaServicio(models.Model):
    id_categoria_servicio = models.BigAutoField(primary_key=True, db_column='id_categoria_servicio')
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categoria_servicio'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    id_servicio = models.BigAutoField(primary_key=True, db_column='id_servicio')
    tipo_servicio = models.ForeignKey(
        TipoServicio,
        db_column='id_tipo_servicio',
        on_delete=models.RESTRICT,
        related_name='servicios',
    )
    categoria_servicio = models.ForeignKey(
        CategoriaServicio,
        db_column='id_categoria_servicio',
        on_delete=models.RESTRICT,
        related_name='servicios',
    )
    nombre = models.CharField(max_length=140)
    descripcion = models.TextField(null=True, blank=True)
    duracion_minutos = models.PositiveIntegerField()
    precio_base = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'servicio'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class EmpleadoServicio(models.Model):
    empleado = models.ForeignKey(
        Empleado,
        db_column='id_usuario_empleado',
        on_delete=models.CASCADE,
        related_name='servicios_asignados',
    )
    servicio = models.ForeignKey(
        Servicio,
        db_column='id_servicio',
        on_delete=models.CASCADE,
        related_name='empleados_asignados',
    )
    duracion_personalizada_minutos = models.PositiveIntegerField(null=True, blank=True)
    precio_personalizado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'empleado_servicio'
        managed = True
        ordering = ['servicio']  # CORRECCIÓN: Uso del campo relacional explícito para el linter


class Agendamiento(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('EN_PROCESO', 'En proceso'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
        ('NO_ASISTIO', 'No asistio'),
    ]

    CANAL_CHOICES = [
        ('WEB', 'Web'),
        ('APP', 'App'),
        ('TELEFONO', 'Telefono'),
        ('LOCAL', 'Local'),
    ]

    id_agendamiento = models.BigAutoField(primary_key=True, db_column='id_agendamiento')
    cliente = models.ForeignKey(
        Cliente,
        db_column='id_usuario_cliente',
        on_delete=models.RESTRICT,
        related_name='agendamientos',
    )
    empleado = models.ForeignKey(
        Empleado,
        db_column='id_usuario_empleado',
        on_delete=models.RESTRICT,
        related_name='agendamientos',
    )
    servicio = models.ForeignKey(
        Servicio,
        db_column='id_servicio',
        on_delete=models.RESTRICT,
        related_name='agendamientos',
    )
    estado = models.CharField(max_length=20, default='PENDIENTE')
    inicia_en = models.DateTimeField()
    termina_en = models.DateTimeField()
    canal = models.CharField(max_length=20, default='WEB')
    notas = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='creado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='agendamientos_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'agendamiento'
        managed = True
        ordering = ['-inicia_en']

    def __str__(self):
        # CORRECCIÓN: Acceso seguro mediante la pk del objeto relacionado para sanear Pylance
        return f"{self.cliente.pk} - {self.servicio.nombre}"


class HistorialEstadoAgendamiento(models.Model):
    id_historial_estado_agendamiento = models.BigAutoField(primary_key=True, db_column='id_historial_estado_agendamiento')
    agendamiento = models.ForeignKey(
        Agendamiento,
        db_column='id_agendamiento',
        on_delete=models.CASCADE,
        related_name='historial_estados',
    )
    estado = models.CharField(max_length=20)
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='cambiado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cambios_estado_agendamiento',
    )
    nota = models.CharField(max_length=255, null=True, blank=True)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_estado_agendamiento'
        managed = True
        ordering = ['-cambiado_en']