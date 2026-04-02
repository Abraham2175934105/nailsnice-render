from django.db import models

# Create your models here.
class ActiveProductoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ProductoMaquillaje(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('no_disponible', 'No Disponible'),
    ]
    id_inventario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    cantidad = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    fecha_ingreso = models.DateField()
    stock = models.PositiveIntegerField(default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2)       
    descripcion = models.CharField(max_length=255, blank=True, default='') 
    marca = models.CharField(max_length=100, default='Sin marca')        
    proveedor = models.CharField(max_length=120, blank=True, default='Sin proveedor')
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} (ID: {self.id_inventario})"
 
    class Meta:
        verbose_name = "Producto de Maquillaje"
        verbose_name_plural = "Productos de Maquillaje"
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['marca']),
            models.Index(fields=['descripcion']),
        ]

    objects = models.Manager()
    activos = ActiveProductoManager()