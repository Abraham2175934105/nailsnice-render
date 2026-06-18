from django import forms
from django.utils import timezone
from datetime import timedelta
import re

from clientes.models import Cliente
from productos.models import VarianteProducto
from inventario.models import SaldoInventario
from .models import PedidoVenta


DIRECCION_COLOMBIA_RE = re.compile(r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+')


class PedidoVentaBaseForm(forms.Form):
    variante = forms.ModelChoiceField(
        queryset=VarianteProducto.objects.select_related('producto').order_by('sku'),
        label='Variante de Producto *',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    cantidad = forms.IntegerField(
        min_value=1,
        label='Cantidad *',
        widget=forms.NumberInput(attrs={'min': '1', 'placeholder': 'Ej: 1', 'class': 'form-input'})
    )
    direccion_linea1 = forms.CharField(
        max_length=160,
        label='Dirección Principal (Calle, Carrera, Número) *',
        widget=forms.TextInput(attrs={'placeholder': 'Calle, número, barrio', 'class': 'form-input'})
    )
    ciudad = forms.CharField(
        max_length=80,
        label='Ciudad *',
        widget=forms.TextInput(attrs={'placeholder': 'Ciudad', 'class': 'form-input'})
    )
    departamento = forms.CharField(
        max_length=80,
        required=False,
        label='Departamento',
        widget=forms.TextInput(attrs={'placeholder': 'Departamento / Estado', 'class': 'form-input'})
    )
    nombre_destinatario = forms.CharField(
        max_length=120,
        required=False,
        label='Nombre Completo del Destinatario *',
        widget=forms.TextInput(attrs={'placeholder': 'Nombre completo del destinatario', 'class': 'form-input'})
    )
    estado = forms.ChoiceField(
        choices=PedidoVenta.ESTADOS,
        initial='PENDIENTE_PAGO',
        label='Estado del Pedido *',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_direccion_linea1(self):
        direccion = (self.cleaned_data.get('direccion_linea1') or '').strip()
        if not direccion:
            raise forms.ValidationError('La dirección es obligatoria.')
        if not DIRECCION_COLOMBIA_RE.match(direccion):
            raise forms.ValidationError('La dirección debe seguir un formato colombiano válido (ej: Calle 123 #45-67).')
        return direccion

    def clean_ciudad(self):
        ciudad = (self.cleaned_data.get('ciudad') or '').strip()
        if not ciudad:
            raise forms.ValidationError('La ciudad es obligatoria.')
        return ciudad

    def clean(self):
        cleaned = super().clean()
        variante = cleaned.get('variante')
        cantidad = cleaned.get('cantidad')
        if variante and cantidad:
            saldo = SaldoInventario.objects.filter(variante=variante).first()
            disponible = 0
            if saldo:
                disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0))
            if cantidad > disponible:
                self.add_error('cantidad', 'Stock insuficiente para la variante seleccionada.')
        return cleaned


class PedidoVentaForm(PedidoVentaBaseForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.select_related('usuario').order_by('usuario__correo'),
        label='Cliente *',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class EmpleadoPedidoForm(PedidoVentaBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cantidad'].widget.attrs.update({'min': '1', 'class': 'form-input'})


class CheckoutForm(forms.Form):
    linea1 = forms.CharField(
        max_length=160,
        required=True,
        label='Dirección Principal *',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Calle 123 #45-67', 'class': 'form-input'})
    )
    linea2 = forms.CharField(
        max_length=160,
        required=False,
        label='Información Adicional',
        widget=forms.TextInput(attrs={'placeholder': 'Apto, bloque, barrio', 'class': 'form-input'})
    )
    ciudad = forms.CharField(
        max_length=80,
        required=True,
        label='Ciudad *',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Bogotá', 'class': 'form-input'})
    )
    departamento = forms.CharField(
        max_length=80,
        required=False,
        label='Departamento',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Cundinamarca', 'class': 'form-input'})
    )
    metodo_pago = forms.ChoiceField(
        choices=[('contraentrega', 'Contraentrega'), ('tarjeta', 'Tarjeta')],
        required=True,
        widget=forms.RadioSelect()
    )

    def clean_linea1(self):
        linea1 = self.cleaned_data.get('linea1', '').strip()
        direccion_pattern = r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+'
        if not re.match(direccion_pattern, linea1):
            raise forms.ValidationError('Usa un formato de vía colombiano (ej: "Calle 123 #45-67").')
        return linea1

    def clean_ciudad(self):
        ciudad = self.cleaned_data.get('ciudad', '').strip()
        if not ciudad:
            raise forms.ValidationError('La ciudad es obligatoria.')
        return ciudad