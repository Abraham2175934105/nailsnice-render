from datetime import date, time, timedelta

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


class EmpleadoAgendamientoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].widget.attrs.update({'autocomplete': 'off'})
        self.fields['servicio'].widget.attrs.update({'autocomplete': 'off'})
        self.fields['fecha_agendamiento'].widget.attrs.update({'min': date.today().isoformat()})
        self.fields['hora_agendamiento'].widget.attrs.update({'step': '300'})
        self.fields['notas'].widget.attrs.update({'maxlength': '300', 'placeholder': 'Observaciones adicionales (opcional)'})

    class Meta:
        model = Agendamiento
        fields = [
            'cliente',
            'servicio',
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

    def clean_fecha_agendamiento(self):
        fecha = self.cleaned_data.get('fecha_agendamiento')
        if not fecha:
            return fecha

        hoy = date.today()
        maximo = hoy + timedelta(days=60)
        if fecha < hoy:
            raise forms.ValidationError('La fecha no puede ser anterior a hoy.')
        if fecha > maximo:
            raise forms.ValidationError('La fecha no puede ser mayor a 60 días desde hoy.')
        return fecha

    def clean_hora_agendamiento(self):
        hora = self.cleaned_data.get('hora_agendamiento')
        if not hora:
            return hora

        hora_inicio = time(7, 0)
        hora_fin = time(20, 0)
        if hora < hora_inicio or hora > hora_fin:
            raise forms.ValidationError('La hora debe estar entre 07:00 y 20:00.')
        return hora

    def clean_notas(self):
        notas = (self.cleaned_data.get('notas') or '').strip()
        if len(notas) > 300:
            raise forms.ValidationError('Las notas no pueden superar los 300 caracteres.')
        return notas

    def clean(self):
        cleaned_data = super().clean()

        servicio = cleaned_data.get('servicio')
        if servicio and str(getattr(servicio, 'estado_servicio', '') or '').strip().lower() != 'activo':
            self.add_error('servicio', 'Solo puedes seleccionar servicios activos.')

        cliente = cleaned_data.get('cliente')
        if cliente:
            usuario = getattr(cliente, 'usuario', None)
            estado = str(getattr(usuario, 'estado_usuario', '') or '').strip().lower()
            if usuario and (not getattr(usuario, 'is_active', True) or estado not in {'', 'activo'}):
                self.add_error('cliente', 'El cliente seleccionado no está activo.')

        fecha = cleaned_data.get('fecha_agendamiento')
        hora = cleaned_data.get('hora_agendamiento')
        empleado = getattr(self.instance, 'empleado', None)
        if empleado and fecha and hora:
            qs = Agendamiento.objects.filter(
                empleado=empleado,
                fecha_agendamiento=fecha,
                hora_agendamiento=hora,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya tienes un agendamiento en esa fecha y hora.')

        return cleaned_data
