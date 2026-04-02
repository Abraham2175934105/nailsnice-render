from django import forms
from .models import Pedidos
from datetime import date, timedelta

class PedidosForm(forms.ModelForm):
    class Meta:
        model = Pedidos
        fields = ['usuario', 'telefono', 'producto', 'precio', 'direccion', 'cantidad', 'fecha']
        labels = {
            'usuario': 'Usuario',
            'telefono': 'Teléfono',
            'producto': 'Producto',
            'precio': 'Precio',
            'direccion': 'Dirección',
            'cantidad': 'Cantidad',
            'fecha': 'Fecha',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'cantidad': forms.NumberInput(attrs={'min': '0'}),
            'precio': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }

    def clean_usuario(self):
        usuario = self.cleaned_data.get('usuario')
        if not usuario.replace(' ', '').isalpha():
            raise forms.ValidationError("El usuario solo puede contener letras.")
        return usuario

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit():
            raise forms.ValidationError("El teléfono solo puede contener números.")
        if len(telefono) != 10:
            raise forms.ValidationError("El teléfono debe tener exactamente 10 dígitos.")
        return telefono

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        if precio < 1000:
            raise forms.ValidationError("El precio mínimo es $1.000 pesos colombianos.")
        return precio

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        hoy = date.today()
        maximo = hoy + timedelta(days=30)
        if fecha < hoy:
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        if fecha > maximo:
            raise forms.ValidationError("La fecha no puede ser mayor a un mes desde hoy.")
        return fecha