from django import forms

from django.core.exceptions import ValidationError
from inventario.models import ProductoMaquillaje
from .models import Producto, Categoria, Marca, Color, UnidadMedida


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'precio',
            'imagen',
            'estado_producto',
            'id_categoria',
            'id_marca',
            'id_color',
            'id_unidad_medida',
            'inventario',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'imagen': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_categoria'].queryset = Categoria.objects.all().order_by('nombre_categoria')
        self.fields['id_marca'].queryset = Marca.objects.all().order_by('nombre_marca')
        self.fields['id_color'].queryset = Color.objects.all().order_by('nombre_color')
        self.fields['id_unidad_medida'].queryset = UnidadMedida.objects.all().order_by('nombre_medida')

        current_inventario = None
        if self.instance and self.instance.pk:
            current_inventario = self.instance.inventario

        available_inv = ProductoMaquillaje.activos.filter(producto_catalogo__isnull=True)
        if current_inventario:
            available_inv = ProductoMaquillaje.activos.filter(pk=current_inventario.pk) | available_inv
        self.fields['inventario'].queryset = available_inv.order_by('nombre')
        self.fields['inventario'].required = True

    def clean_inventario(self):
        inventario = self.cleaned_data.get('inventario')
        if not inventario:
            raise forms.ValidationError('Debes asociar un ítem de inventario.')

        qs = Producto.objects.filter(inventario=inventario)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ese inventario ya está vinculado a otro producto.')
        return inventario

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if not imagen:
            return imagen
        content_type = getattr(imagen, 'content_type', '')
        if content_type and not content_type.startswith('image/'):
            raise ValidationError('Solo se permiten archivos de imagen.')
        if hasattr(imagen, 'size') and imagen.size > 5 * 1024 * 1024:
            raise ValidationError('La imagen no debe superar 5 MB.')
        return imagen


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre_categoria']


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre_marca']


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['nombre_color']


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['nombre_medida']
