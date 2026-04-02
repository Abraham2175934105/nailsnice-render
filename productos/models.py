from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from inventario.models import ProductoMaquillaje


class Categoria(models.Model):
    nombre_categoria = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nombre_categoria']

    def __str__(self):
        return self.nombre_categoria


class Marca(models.Model):
    nombre_marca = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nombre_marca']

    def __str__(self):
        return self.nombre_marca


class Color(models.Model):
    nombre_color = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Color'
        verbose_name_plural = 'Colores'
        ordering = ['nombre_color']

    def __str__(self):
        return self.nombre_color


class UnidadMedida(models.Model):
    UNIDADES = [
        ('Mililitro', 'Mililitro (ml)'),
        ('Unidad', 'Unidad'),
        ('Miligramo', 'Miligramo (mg)'),
        ('Gramo', 'Gramo (g)'),
        ('Set', 'Set'),
    ]

    nombre_medida = models.CharField(max_length=50, choices=UNIDADES, unique=True)

    class Meta:
        verbose_name = 'Unidad de Medida'
        verbose_name_plural = 'Unidades de Medida'

    def __str__(self):
        return self.nombre_medida


class Producto(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Descontinuado', 'Descontinuado'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(
        help_text='Descripcion minima de 10 caracteres',
        validators=[MinLengthValidator(10)],
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    imagen = models.ImageField(upload_to='productos_catalogo/', blank=True, null=True)
    estado_producto = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Activo'
    )

    id_categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    id_marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    id_color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    id_unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.SET_NULL, null=True, blank=True)

    inventario = models.OneToOneField(
        ProductoMaquillaje,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        unique=True,
        related_name='producto_catalogo'
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-creado_en']

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or '').strip()
        self.descripcion = (self.descripcion or '').strip()

    def __str__(self):
        return self.nombre
