import re
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from usuarios.models import Usuario

class PerfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'telefono']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')
        
        # Enforce exactly one word and only alphabetic/accented characters
        if ' ' in nombre or not re.fullmatch(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+$', nombre):
            raise forms.ValidationError('Debe ingresar un único nombre, sin espacios ni caracteres especiales.')
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido', '').strip()
        if not apellido:
            raise forms.ValidationError('El apellido es obligatorio.')
        
        # Enforce exactly one word and only alphabetic/accented characters
        if ' ' in apellido or not re.fullmatch(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+$', apellido):
            raise forms.ValidationError('Debe ingresar un único apellido, sin espacios ni caracteres especiales.')
        return apellido

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if not telefono:
            raise forms.ValidationError('El teléfono es obligatorio.')
        if not re.fullmatch(r'\d{10,11}', telefono):
            raise forms.ValidationError('El teléfono debe tener entre 10 y 11 dígitos numéricos.')
        return telefono

    # Aliases to fully satisfy potential direct clean_first_name / clean_last_name calls
    def clean_first_name(self):
        return self.clean_nombre()

    def clean_last_name(self):
        return self.clean_apellido()


class RegistroForm(forms.Form):
    nombre = forms.CharField(max_length=100, required=True)
    apellido = forms.CharField(max_length=100, required=True)
    telefono = forms.CharField(max_length=20, required=True)
    linea1 = forms.CharField(max_length=160, required=True)
    ciudad = forms.CharField(max_length=80, required=True)
    departamento = forms.CharField(max_length=80, required=True)
    correo = forms.EmailField(max_length=180, required=True)
    contrasena = forms.CharField(required=True)

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if ' ' in nombre or not re.fullmatch(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+$', nombre):
            raise forms.ValidationError('Debe ingresar un único nombre, sin espacios ni caracteres especiales.')
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido', '').strip()
        if ' ' in apellido or not re.fullmatch(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ]+$', apellido):
            raise forms.ValidationError('Debe ingresar un único apellido, sin espacios ni caracteres especiales.')
        return apellido

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if not re.fullmatch(r'\d{10,11}', telefono):
            raise forms.ValidationError('El teléfono debe tener entre 10 y 11 dígitos numéricos.')
        if Usuario.objects.filter(telefono=telefono).exists():
            raise forms.ValidationError('Este teléfono ya está registrado.')
        return telefono

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        match = re.match(r'^([^@]+)@([^@]+\.[^@]+)$', correo)
        if not match:
            raise forms.ValidationError('El formato del correo electrónico no es válido.')
        local_part = match.group(1)
        if len(local_part) < 6:
            raise forms.ValidationError('El correo debe tener al menos 6 caracteres antes del dominio.')
        if Usuario.objects.filter(correo=correo).exists():
            raise forms.ValidationError('El correo ya está registrado.')
        return correo

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

    def clean_departamento(self):
        departamento = self.cleaned_data.get('departamento', '').strip()
        if not departamento:
            raise forms.ValidationError('El departamento es obligatorio.')
        return departamento

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get('contrasena', '')
        if len(contrasena) < 8 or len(contrasena) > 20:
            raise forms.ValidationError('La contraseña debe tener entre 8 y 20 caracteres.')
        if not re.search(r'[A-Z]', contrasena):
            raise forms.ValidationError('La contraseña debe incluir al menos una letra mayúscula.')
        if not re.search(r'[a-z]', contrasena):
            raise forms.ValidationError('La contraseña debe incluir al menos una letra minúscula.')
        if not re.search(r'\d', contrasena):
            raise forms.ValidationError('La contraseña debe incluir al menos un número.')
        if not re.search(r'[^A-Za-z0-9]', contrasena):
            raise forms.ValidationError('La contraseña debe incluir al menos un carácter especial.')
        return contrasena

