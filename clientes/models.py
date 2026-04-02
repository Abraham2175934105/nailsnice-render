from django.core.validators import MinValueValidator
from django.db import models
from usuarios.models import Usuario

class Cliente(models.Model):
    direccion = models.CharField(max_length=255, blank=True, null=True)
    puntos_fidelidad = models.IntegerField(
        default=0,
        help_text='Puntos de fidelidad acumulados',
        validators=[MinValueValidator(0)],
    )
    
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='cliente')
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['usuario__nombre1']
    
    def clean(self):
        super().clean()
        if self.direccion:
            self.direccion = self.direccion.strip()

    def __str__(self):
        return f"Cliente: {self.usuario.email}"


class ServicioCliente(models.Model):
    CANAL_CHOICES = [
        ('WhatsApp', 'WhatsApp'),
        ('Email', 'Email'),
        ('Teléfono', 'Teléfono'),
        ('Presencial', 'Presencial'),
    ]
    
    CONTROL_CHOICES = [
        ('Agendado', 'Agendado'),
        ('Pendiente', 'Pendiente'),
        ('Completado', 'Completado'),
    ]
    
    ESTADO_TICKET_CHOICES = [
        ('Abierto', 'Abierto'),
        ('Cerrado', 'Cerrado'),
        ('En espera', 'En espera'),
    ]
    
    canal_comunicacion = models.CharField(max_length=50, choices=CANAL_CHOICES)
    control_agendamiento = models.CharField(max_length=20, choices=CONTROL_CHOICES, default='Pendiente')
    cupones = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    estado_ticket = models.CharField(max_length=20, choices=ESTADO_TICKET_CHOICES, default='Abierto')
    fecha_contacto = models.DateField(auto_now_add=True)
    promociones = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='servicios_cliente')
    
    class Meta:
        verbose_name = 'Servicio al Cliente'
        verbose_name_plural = 'Servicios al Cliente'
        ordering = ['-fecha_contacto']
    
    def __str__(self):
        return f"Ticket {self.id} - {self.cliente.usuario.email} - {self.estado_ticket}"
