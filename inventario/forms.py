from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ProductoMaquillaje
 

class ProductoMaquillajeForm(forms.ModelForm):
    class Meta:
        model = ProductoMaquillaje
        fields = ['nombre', 'cantidad', 'estado', 'fecha_ingreso', 'stock', 'precio', 'descripcion', 'marca', 'proveedor', 'imagen']
        widgets = {
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
            'cantidad': forms.NumberInput(attrs={'min': '0'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
            'precio': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
        labels = {
            'nombre': 'Nombre del Producto',
            'cantidad': 'Cantidad',
            'estado': 'Estado',
            'fecha_ingreso': 'Fecha de Ingreso',
            'stock': 'Stock Disponible',
            'precio': 'Precio',
            'descripcion': 'Descripción',
            'marca': 'Marca',
            'proveedor': 'Proveedor',
            'imagen': 'Imagen',
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise ValidationError('El nombre es obligatorio.')
        if len(nombre) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')
        return nombre

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get('descripcion') or '').strip()
        if len(descripcion) < 5:
            raise ValidationError('Incluye una descripción de al menos 5 caracteres.')
        return descripcion

    def clean_marca(self):
        marca = (self.cleaned_data.get('marca') or '').strip()
        if not marca:
            raise ValidationError('La marca es obligatoria.')
        return marca[:100]

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        if not fecha:
            raise ValidationError('La fecha de ingreso es obligatoria.')
        today = timezone.now().date()
        if fecha > today:
            raise ValidationError('La fecha de ingreso no puede ser futura.')
        return fecha

    def clean_proveedor(self):
        proveedor = (self.cleaned_data.get('proveedor') or '').strip()
        return proveedor or 'Sin proveedor'

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None or precio <= 0:
            raise ValidationError('El precio debe ser mayor a 0.')
        return precio

    def clean(self):
        cleaned = super().clean()
        cantidad = cleaned.get('cantidad') or 0
        stock = cleaned.get('stock') or 0
        if cantidad < 0:
            self.add_error('cantidad', 'La cantidad no puede ser negativa.')
        if stock < 0:
            self.add_error('stock', 'El stock no puede ser negativo.')
        if cantidad and stock and stock > cantidad:
            self.add_error('stock', 'El stock no puede superar la cantidad ingresada.')
        return cleaned

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if not imagen:
            return imagen
        content_type = getattr(imagen, 'content_type', '')
        if content_type and not content_type.startswith('image/'):
            raise ValidationError('Solo se permiten archivos de imagen.')
        if imagen.size > 5 * 1024 * 1024:
            raise ValidationError('La imagen no debe superar 5 MB.')
        return imagen