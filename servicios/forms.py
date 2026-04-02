from django import forms

from .models import Agendamiento


class AgendamientoForm(forms.ModelForm):
    class Meta:
        model = Agendamiento
        fields = [
            'cliente',
            'servicio',
            'empleado',
            'fecha_agendamiento',
            'hora_agendamiento',
            'estado_agendamiento',
            'notas',
        ]
        widgets = {
            'fecha_agendamiento': forms.DateInput(attrs={'type': 'date'}),
            'hora_agendamiento': forms.TimeInput(attrs={'type': 'time'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }
