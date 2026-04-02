from django.db import models
from django.core.validators import MinValueValidator

class TipoServicio(models.Model):
    TIPOS = [
        ('Manicura', 'Manicura'),
        ('Pedicura', 'Pedicura'),
        ('Maquillaje', 'Maquillaje'),
        ('Tratamiento Facial', 'Tratamiento Facial'),
        ('Depilación', 'Depilación'),
    ]
    
    nombre_tipo = models.CharField(max_length=255, choices=TIPOS, unique=True)
    
    class Meta:
        verbose_name = 'Tipo de Servicio'
        verbose_name_plural = 'Tipos de Servicio'
        ordering = ['nombre_tipo']
    
    def __str__(self):
        return self.nombre_tipo


class Servicio(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Descontinuado', 'Descontinuado'),
    ]
    
    nombre_servicio = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    precio_servicio = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)]
    )
    duracion_servicio = models.CharField(
        max_length=255,
        help_text='Ej: 30m, 1h, 1.5h'
    )
    duracion_estimada = models.IntegerField(blank=True, null=True, help_text='Duración en minutos')
    categoria_servicio = models.CharField(max_length=255)
    estado_servicio = models.CharField(
        max_length=255,
        choices=ESTADO_CHOICES,
        default='Activo'
    )
    
    tipo_servicio = models.ForeignKey(TipoServicio, on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['nombre_servicio']
    
    def clean(self):
        super().clean()
        self.nombre_servicio = (self.nombre_servicio or '').strip()
        self.categoria_servicio = (self.categoria_servicio or '').strip()
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        if self.duracion_estimada is not None and self.duracion_estimada < 0:
            from django.core.exceptions import ValidationError
            raise ValidationError({'duracion_estimada': 'La duracion estimada no puede ser negativa.'})

    def __str__(self):
        return self.nombre_servicio


class Agendamiento(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Confirmado', 'Confirmado'),
        ('Completado', 'Completado'),
        ('Cancelado', 'Cancelado'),
        ('No presentado', 'No presentado'),
    ]
    
    fecha_agendamiento = models.DateField()
    hora_agendamiento = models.TimeField()
    estado_agendamiento = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Pendiente'
    )
    notas = models.TextField(blank=True, null=True)
    
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='agendamientos')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='agendamientos')
    empleado = models.ForeignKey(
        'usuarios.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agendamientos'
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Agendamiento'
        verbose_name_plural = 'Agendamientos'
        ordering = ['-fecha_agendamiento', 'hora_agendamiento']
        unique_together = ('fecha_agendamiento', 'hora_agendamiento', 'empleado')
    
    def __str__(self):
        return f"{self.cliente.usuario.email} - {self.servicio.nombre_servicio} ({self.fecha_agendamiento})"
