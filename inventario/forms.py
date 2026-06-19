from django import forms
from django.core.exceptions import ValidationError

from productos.models import VarianteProducto, Producto
from .models import Bodega, SaldoInventario, TipoMovimientoInventario, MovimientoInventario


class VarianteProductoForm(forms.ModelForm):
    # ---- Campos extra (no-model): editan directamente el Producto padre ----
    nombre_producto = forms.CharField(
        required=False,
        label="Nombre del Producto",
        max_length=160,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Ej: Labial SuperStay Mate',
        }),
        help_text="Nombre real del producto que verán los clientes en el catálogo.",
    )
    descripcion = forms.CharField(
        required=False,
        label="Descripción del Producto",
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Describe el producto: características, uso, ingredientes…',
        }),
        help_text="Descripción que aparece en la página de detalle del catálogo.",
    )
    imagen = forms.FileField(
        required=False,
        label="Imagen del Producto",
        widget=forms.FileInput(attrs={'class': 'form-input'}),
    )

    class Meta:
        model = VarianteProducto
        fields = [
            'producto',
            'sku',
            'codigo_barras',
            'nombre_variante',
            'precio',
            'costo',
            'peso_gramos',
            'activo',
        ]
        widgets = {
            # El select queda oculto; se usa sólo en creación, en edición se sustituye por nombre_producto.
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: SKU-001'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Opcional'}),
            'nombre_variante': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Rojo, 50ml, Talla M… (deja vacío si no aplica)',
            }),
            'precio': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'class': 'form-input'}),
            'costo': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'class': 'form-input'}),
            'peso_gramos': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'class': 'form-input'}),
        }
        labels = {
            'producto': 'Producto (catálogo)',
            'sku': 'SKU',
            'codigo_barras': 'Código de barras',
            'nombre_variante': 'Variante / Presentación',
            'precio': 'Precio de venta',
            'costo': 'Costo de compra',
            'peso_gramos': 'Peso (g)',
            'activo': 'Activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.select_related('subcategoria').order_by('nombre')
        # Pre-poblar los campos extra desde el Producto relacionado (modo edición)
        instance = kwargs.get('instance')
        if instance and instance.pk and hasattr(instance, 'producto') and instance.producto_id:
            try:
                prod = instance.producto
                self.fields['nombre_producto'].initial = prod.nombre
                self.fields['descripcion'].initial = (
                    prod.descripcion_corta or prod.descripcion_larga or ''
                )
            except Exception:
                pass


class SaldoInventarioForm(forms.ModelForm):
    class Meta:
        model = SaldoInventario
        fields = ['bodega', 'cantidad_existencia', 'cantidad_reservada', 'nivel_reorden']
        widgets = {
            'bodega': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_existencia': forms.NumberInput(attrs={'min': '0', 'class': 'form-input'}),
            'cantidad_reservada': forms.NumberInput(attrs={'min': '0', 'class': 'form-input'}),
            'nivel_reorden': forms.NumberInput(attrs={'min': '0', 'class': 'form-input'}),
        }
        labels = {
            'bodega': 'Bodega',
            'cantidad_existencia': 'Stock',
            'cantidad_reservada': 'Reservado',
            'nivel_reorden': 'Nivel reorden',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bodega'].queryset = Bodega.objects.filter(activo=True).order_by('nombre')

    def clean(self):
        cleaned = super().clean()
        existencia = cleaned.get('cantidad_existencia')
        reservada = cleaned.get('cantidad_reservada')
        if existencia is not None and reservada is not None and reservada > existencia:
            raise ValidationError('La cantidad reservada no puede superar la existencia.')
        return cleaned


class MovimientoInventarioForm(forms.ModelForm):
    """Formulario para registrar entradas y salidas de inventario."""
    class Meta:
        model = MovimientoInventario
        fields = ['tipo_movimiento', 'bodega', 'notas']
        labels = {
            'tipo_movimiento': 'Tipo de movimiento',
            'bodega': 'Bodega',
            'notas': 'Notas',
        }
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_movimiento'].queryset = TipoMovimientoInventario.objects.all().order_by('descripcion')
        self.fields['bodega'].queryset = Bodega.objects.filter(activo=True).order_by('nombre')


class ItemMovimientoForm(forms.Form):
    """Formulario para cada item (variante + cantidad) dentro de un movimiento."""
    variante = forms.ModelChoiceField(
        queryset=VarianteProducto.objects.filter(activo=True).select_related('producto').order_by('producto__nombre'),
        label='Variante',
    )
    cantidad = forms.IntegerField(min_value=1, label='Cantidad')
    costo_unitario = forms.DecimalField(
        min_value=0,
        required=False,
        label='Costo unitario',
        widget=forms.NumberInput(attrs={'step': '0.01'}),
    )


# Form de compatibilidad usado por tests antiguos que esperaban
# `ProductoMaquillajeForm` en el módulo `inventario.forms`.
from .models import ProductoMaquillaje


class ProductoMaquillajeForm(forms.ModelForm):
    imagen = forms.FileField(required=False)

    class Meta:
        model = ProductoMaquillaje
        fields = [
            'nombre',
            'cantidad',
            'estado',
            'fecha_ingreso',
            'stock',
            'precio',
            'descripcion',
            'marca',
            'proveedor',
            'imagen',
            'is_active',
        ]

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        if fecha:
            from django.utils import timezone
            if fecha > timezone.now().date():
                raise ValidationError('La fecha de ingreso no puede ser futura.')
        return fecha

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise ValidationError('El nombre es requerido.')
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio in (None, ''):
            raise ValidationError('El precio es requerido.')
        try:
            from decimal import Decimal
            Decimal(str(precio))
        except Exception:
            raise ValidationError('Precio inválido.')
        return precio

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None:
            return stock
        try:
            if int(stock) < 0:
                raise ValidationError('Stock no puede ser negativo.')
        except (TypeError, ValueError):
            raise ValidationError('Stock inválido.')
        return stock

    def clean_descripcion(self):
        desc = (self.cleaned_data.get('descripcion') or '').strip()
        if not desc:
            raise ValidationError('La descripción es requerida.')
        return desc

    def save(self, commit=True):
        instance = super().save(commit=False)
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            instance.imagen = getattr(imagen, 'name', str(imagen))
        if commit:
            instance.save()
        return instance