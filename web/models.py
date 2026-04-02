from django.db import models


class ActiveClienteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Clientes(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    direccion = models.CharField(max_length=100)
    telefono = models.CharField(max_length=100)
    correo = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    objects = models.Manager()
    activos = ActiveClienteManager()

    def __str__(self):
        return f"{self.nombre} {self.apellido}".strip() or str(self.id)