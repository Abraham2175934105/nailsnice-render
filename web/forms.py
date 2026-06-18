import re

from django import forms

from clientes.models import Cliente
from usuarios.models import RolAcceso, Usuario, UsuarioRol

ESTADO_CHOICES = [
    ('ACTIVO', 'Activo'),
    ('INACTIVO', 'Inactivo'),
    ('BLOQUEADO', 'Bloqueado'),
]

class ClienteForm(forms.Form):
    correo = forms.EmailField(label='Correo', max_length=150)
    nombre = forms.CharField(label='Nombre(s)', max_length=80, required=False)
    apellido = forms.CharField(label='Apellido(s)', max_length=80, required=False)
    telefono = forms.CharField(label='Telefono', max_length=30, required=False)
    acepta_fidelizacion = forms.BooleanField(label='Deseo ser parte del plan de fidelización', required=False, initial=True)
    estado = forms.ChoiceField(label='Estado', choices=ESTADO_CHOICES)
    rol = forms.ModelChoiceField(queryset=RolAcceso.objects.none(), required=False, label='Rol')
    es_staff = forms.BooleanField(label='Es staff', required=False)
    es_superusuario = forms.BooleanField(label='Es superusuario', required=False)
    password = forms.CharField(
        max_length=128,
        required=False,
        label='Contrasena',
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Opcional. Si la dejas vacia, se conserva la contrasena actual.',
    )

    def __init__(self, *args, usuario=None, perfil=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_instance = usuario
        self.perfil_instance = perfil
        self.fields['rol'].queryset = RolAcceso.objects.all().order_by('nombre')

        role_cliente, _ = RolAcceso.objects.get_or_create(
            nombre='Cliente',
            defaults={'descripcion': 'Cliente', 'codigo': 'CLIENTE'},
        )
        self.fields['rol'].initial = role_cliente

        if usuario:
            self.fields['correo'].initial = usuario.correo
            self.fields['nombre'].initial = usuario.nombre or ''
            self.fields['apellido'].initial = usuario.apellido or ''
            self.fields['telefono'].initial = usuario.telefono or ''
            self.fields['estado'].initial = usuario.estado or 'ACTIVO'
            self.fields['es_staff'].initial = bool(usuario.is_staff)
            self.fields['es_superusuario'].initial = bool(usuario.is_superuser)
            if getattr(usuario, 'rol_asignado', None) and getattr(usuario.rol_asignado, 'rol', None):
                self.fields['rol'].initial = usuario.rol_asignado.rol

        if perfil:
            self.fields['acepta_fidelizacion'].initial = perfil.acepta_fidelizacion

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if nombre and not re.fullmatch(r'[A-Za-z\s]+', nombre):
            raise forms.ValidationError('El nombre solo puede contener letras y espacios.')
        return nombre

    def clean_apellido(self):
        apellido = (self.cleaned_data.get('apellido') or '').strip()
        if apellido and not re.fullmatch(r'[A-Za-z\s]+', apellido):
            raise forms.ValidationError('El apellido solo puede contener letras y espacios.')
        return apellido

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()
        if telefono and not telefono.isdigit():
            raise forms.ValidationError('El telefono solo puede contener numeros.')
        if telefono and len(telefono) not in {7, 10, 11}:
            raise forms.ValidationError('El telefono debe tener 7, 10 o 11 digitos.')
        return telefono

    def clean_password(self):
        password = (self.cleaned_data.get('password') or '').strip()
        if not password:
            return ''
        if len(password) < 8 or len(password) > 20:
            raise forms.ValidationError('La contrasena debe tener entre 8 y 20 caracteres.')
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('La contrasena debe incluir al menos una mayuscula.')
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('La contrasena debe incluir al menos una minuscula.')
        if not re.search(r'\d', password):
            raise forms.ValidationError('La contrasena debe incluir al menos un numero.')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError('La contrasena debe incluir al menos un caracter especial.')
        return password

    def save(self):
        data = self.cleaned_data
        rol = data.get('rol')
        role_cliente, _ = RolAcceso.objects.get_or_create(
            nombre='Cliente',
            defaults={'descripcion': 'Cliente', 'codigo': 'CLIENTE'},
        )
        rol = rol or role_cliente

        usuario = self.usuario_instance or Usuario()
        usuario.correo = data['correo'].strip().lower()
        usuario.nombre = data.get('nombre') or None
        usuario.apellido = data.get('apellido') or None
        usuario.telefono = data.get('telefono') or None
        usuario.estado = data.get('estado') or 'ACTIVO'
        usuario.is_staff = bool(data.get('es_staff'))
        usuario.is_superuser = bool(data.get('es_superusuario'))

        raw_password = data.get('password')
        if raw_password:
            usuario.set_password(raw_password)
        elif not usuario.pk:
            usuario.set_unusable_password()

        usuario.save()

        perfil = self.perfil_instance
        if not perfil:
            perfil = Cliente(usuario=usuario)
        perfil.acepta_fidelizacion = data.get('acepta_fidelizacion', False)
        perfil.save()

        if rol:
            UsuarioRol.objects.update_or_create(usuario=usuario, defaults={'rol': rol})

        return usuario, perfil
