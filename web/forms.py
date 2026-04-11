import re

from django import forms

from .models import Clientes
from usuarios.models import Rol, Usuario

class ClientesForm(forms.ModelForm):
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.none(),
        required=False,
        empty_label=None,
        label='Rol',
    )
    nombre1 = forms.CharField(max_length=50, required=False, label='Primer nombre')
    nombre2 = forms.CharField(max_length=50, required=False, label='Segundo nombre')
    apellido1 = forms.CharField(max_length=50, required=False, label='Primer apellido')
    apellido2 = forms.CharField(max_length=50, required=False, label='Segundo apellido')
    password = forms.CharField(
        max_length=128,
        required=False,
        label='Contraseña',
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Opcional. Si la dejas vacía, la contraseña actual se conserva.',
    )

    class Meta:
        model = Clientes
        fields = ['nombre', 'apellido', 'direccion', 'telefono', 'correo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].queryset = Rol.objects.all().order_by('nombre')

        role_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE, defaults={'descripcion': 'Cliente'})
        self.fields['rol'].initial = role_cliente

        instance = getattr(self, 'instance', None)
        self.fields['nombre1'].initial = getattr(instance, 'nombre', '') if instance else ''
        self.fields['apellido1'].initial = getattr(instance, 'apellido', '') if instance else ''
        if instance and getattr(instance, 'pk', None):
            user = Usuario.objects.filter(email__iexact=getattr(instance, 'correo', '')).select_related('id_rol').first()
            if user:
                if user.id_rol_id:
                    self.fields['rol'].initial = user.id_rol
                self.fields['nombre1'].initial = user.nombre1 or self.fields['nombre1'].initial
                self.fields['nombre2'].initial = user.nombre2 or ''
                self.fields['apellido1'].initial = user.apellido1 or self.fields['apellido1'].initial
                self.fields['apellido2'].initial = user.apellido2 or ''

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not nombre.replace(' ', '').isalpha():
            raise forms.ValidationError("El nombre solo puede contener letras.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido')
        if not apellido.replace(' ', '').isalpha():
            raise forms.ValidationError("El apellido solo puede contener letras.")
        return apellido

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit():
            raise forms.ValidationError("El teléfono solo puede contener números.")
        if len(telefono) != 10:
            raise forms.ValidationError("El teléfono debe tener exactamente 10 dígitos.")
        return telefono

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if '@' not in correo:
            raise forms.ValidationError("El correo debe contener @.")
        return correo

    def clean_nombre1(self):
        nombre1 = (self.cleaned_data.get('nombre1') or '').strip()
        if nombre1 and not nombre1.replace(' ', '').isalpha():
            raise forms.ValidationError("El primer nombre solo puede contener letras.")
        return nombre1

    def clean_nombre2(self):
        nombre2 = (self.cleaned_data.get('nombre2') or '').strip()
        if nombre2 and not nombre2.replace(' ', '').isalpha():
            raise forms.ValidationError("El segundo nombre solo puede contener letras.")
        return nombre2

    def clean_apellido1(self):
        apellido1 = (self.cleaned_data.get('apellido1') or '').strip()
        if apellido1 and not apellido1.replace(' ', '').isalpha():
            raise forms.ValidationError("El primer apellido solo puede contener letras.")
        return apellido1

    def clean_apellido2(self):
        apellido2 = (self.cleaned_data.get('apellido2') or '').strip()
        if apellido2 and not apellido2.replace(' ', '').isalpha():
            raise forms.ValidationError("El segundo apellido solo puede contener letras.")
        return apellido2

    def clean_password(self):
        password = (self.cleaned_data.get('password') or '').strip()
        if not password:
            return ''

        if len(password) < 8 or len(password) > 20:
            raise forms.ValidationError('La contraseña debe tener entre 8 y 20 caracteres.')
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('La contraseña debe incluir al menos una mayúscula.')
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('La contraseña debe incluir al menos una minúscula.')
        if not re.search(r'\d', password):
            raise forms.ValidationError('La contraseña debe incluir al menos un número.')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError('La contraseña debe incluir al menos un carácter especial.')
        return password

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if rol:
            return rol

        role_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE, defaults={'descripcion': 'Cliente'})
        return role_cliente