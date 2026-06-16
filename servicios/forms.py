from datetime import timedelta

from django import forms
from django.utils import timezone

from clientes.models import Cliente
from usuarios.models import Empleado
from .models import Agendamiento, Servicio, CategoriaServicio, TipoServicio, EmpleadoServicio


class AgendamientoForm(forms.ModelForm):
    class Meta:
        model = Agendamiento
        fields = [
            'cliente',
            'empleado',
            'servicio',
            'inicia_en',
            'termina_en',
            'estado',
            'canal',
            'notas',
        ]
        widgets = {
            'inicia_en': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'termina_en': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.select_related('usuario').order_by('usuario_id')
        self.fields['servicio'].queryset = Servicio.objects.filter(activo=True).order_by('nombre')

    def clean(self):
        cleaned = super().clean()
        inicia_en = cleaned.get('inicia_en')
        termina_en = cleaned.get('termina_en')

        if inicia_en and termina_en and termina_en <= inicia_en:
            raise forms.ValidationError('La hora de fin debe ser posterior al inicio.')

        if inicia_en:
            if inicia_en < timezone.now() - timedelta(minutes=5):
                self.add_error('inicia_en', 'La fecha y hora no pueden estar en el pasado.')

        empleado = cleaned.get('empleado')
        if empleado and inicia_en and termina_en:
            qs = Agendamiento.objects.filter(
                empleado=empleado,
                estado__in={'PENDIENTE', 'CONFIRMADO', 'EN_PROCESO'},
                inicia_en__lt=termina_en,
                termina_en__gt=inicia_en,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Conflicto de horario: el empleado ya tiene una cita en ese rango.')

        return cleaned


class EmpleadoAgendamientoForm(AgendamientoForm):
    class Meta(AgendamientoForm.Meta):
        fields = [
            'cliente',
            'servicio',
            'inicia_en',
            'termina_en',
            'estado',
            'canal',
            'notas',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].widget.attrs.update({'autocomplete': 'off'})
        self.fields['servicio'].widget.attrs.update({'autocomplete': 'off'})
        self.fields['notas'].widget.attrs.update({'maxlength': '300', 'placeholder': 'Observaciones adicionales (opcional)'})


# ========== FORMULARIOS PARA SERVICIOS ==========

class TipoServicioForm(forms.ModelForm):
    class Meta:
        model = TipoServicio
        fields = ['codigo', 'nombre', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: MANICURE'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Manicura'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoriaServicioForm(forms.ModelForm):
    class Meta:
        model = CategoriaServicio
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Uñas Acrílicas'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción breve'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['tipo_servicio', 'categoria_servicio', 'nombre', 'descripcion', 'duracion_minutos', 'precio_base', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del servicio'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'En minutos'}),
            'precio_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'tipo_servicio': forms.Select(attrs={'class': 'form-control'}),
            'categoria_servicio': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmpleadoServicioForm(forms.ModelForm):
    class Meta:
        model = EmpleadoServicio
        fields = ['empleado', 'servicio', 'duracion_personalizada_minutos', 'precio_personalizado', 'activo']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control'}),
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'duracion_personalizada_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Opcional'}),
            'precio_personalizado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Opcional'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo empleados activos
        self.fields['empleado'].queryset = Empleado.objects.filter(activo=True).select_related('usuario')
        self.fields['servicio'].queryset = Servicio.objects.filter(activo=True)
