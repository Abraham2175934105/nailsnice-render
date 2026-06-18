from django import forms
from django.contrib.auth import get_user_model

from .models import Cliente, DireccionUsuario

Usuario = get_user_model()


# ===========================================================================
# ClienteForm — crea o edita un cliente (usuario + perfil)
# ===========================================================================

class ClienteForm(forms.ModelForm):
    """
    Formulario unificado: maneja campos de Usuario + campos de Cliente.
    - En CREACIÓN: password obligatorio.
    - En EDICIÓN:  password opcional (en blanco = no cambia).
    """

    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
    )
    nombre = forms.CharField(
        max_length=120,
        label='Nombre',
    )
    apellido = forms.CharField(
        max_length=120,
        label='Apellido',
        required=False,
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres'}),
        required=False,
        help_text='Dejar en blanco para no cambiar (solo en edición).',
    )

    class Meta:
        model = Cliente
        fields = ['acepta_fidelizacion']
        widgets = {
            'acepta_fidelizacion': forms.CheckboxInput(
                attrs={'class': 'form-checkbox'}
            ),
        }

    # ------------------------------------------------------------------
    # Inicialización: pre-carga campos del usuario en modo edición
    # ------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        editing = self.instance and self.instance.pk

        if editing:
            u = self.instance.usuario
            self.fields['correo'].initial = u.correo
            self.fields['nombre'].initial = getattr(u, 'nombre', '')
            self.fields['apellido'].initial = getattr(u, 'apellido', '')
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

    # ------------------------------------------------------------------
    # Validación de contraseña mínima solo cuando se proporciona
    # ------------------------------------------------------------------

    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        if pwd and len(pwd) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return pwd

    # ------------------------------------------------------------------
    # Guardado: actualiza o crea usuario + cliente en una sola llamada
    # ------------------------------------------------------------------

    def save(self, commit=True):
        cliente = super().save(commit=False)
        cd = self.cleaned_data

        if cliente.pk:
            # ---------- EDICIÓN ----------
            u = cliente.usuario
            u.correo = cd['correo']
            if hasattr(u, 'nombre'):
                u.nombre = cd.get('nombre', '')
            if hasattr(u, 'apellido'):
                u.apellido = cd.get('apellido', '')
            if cd.get('password'):
                u.set_password(cd['password'])
            if commit:
                u.save()
                cliente.save()

        else:
            # ---------- CREACIÓN ----------
            from usuarios.models import RolAcceso, UsuarioRol  # import local para evitar ciclo

            u = Usuario.objects.create_user(
                correo=cd['correo'],
                nombre=cd.get('nombre', ''),
                apellido=cd.get('apellido', ''),
                password=cd['password'],
            )

            # Asignar rol 'Cliente' automáticamente
            rol_cliente, _ = RolAcceso.objects.get_or_create(
                nombre='Cliente',
                defaults={'codigo': 'CLIENTE'},
            )
            UsuarioRol.objects.create(usuario=u, rol=rol_cliente)

            cliente.usuario = u
            if commit:
                cliente.save()

        return cliente


# ===========================================================================
# DireccionUsuarioForm — crea o edita una dirección
# ===========================================================================

class DireccionUsuarioForm(forms.ModelForm):
    """
    El campo 'usuario' NO se incluye aquí; la vista lo asigna manualmente
    con `direccion.usuario = cliente.usuario` antes de llamar a save().
    """

    class Meta:
        model = DireccionUsuario
        fields = [
            'tipo_direccion',
            'etiqueta',
            'nombre_destinatario',
            'linea1',
            'linea2',
            'ciudad',
            'departamento',
            'codigo_postal',
            'codigo_pais',
            'es_predeterminada_envio',
            'es_predeterminada_factura',
        ]
        widgets = {
            'tipo_direccion': forms.Select(attrs={'class': 'form-select'}),
            'etiqueta': forms.TextInput(attrs={'placeholder': 'Ej: Casa, Oficina'}),
            'nombre_destinatario': forms.TextInput(attrs={'placeholder': 'Nombre completo del destinatario'}),
            'linea1': forms.TextInput(attrs={'placeholder': 'Calle, número, barrio'}),
            'linea2': forms.TextInput(attrs={'placeholder': 'Apartamento, piso, referencia (opcional)'}),
            'ciudad': forms.TextInput(attrs={'placeholder': 'Ciudad'}),
            'departamento': forms.TextInput(attrs={'placeholder': 'Departamento / Estado'}),
            'codigo_postal': forms.TextInput(attrs={'placeholder': 'Ej: 110111'}),
            'codigo_pais': forms.TextInput(attrs={
                'maxlength': 2,
                'placeholder': 'CO',
                'style': 'text-transform:uppercase; width:60px',
            }),
        }

    def clean_codigo_pais(self):
        value = self.cleaned_data.get('codigo_pais', 'CO')
        value = value.strip().upper()
        if len(value) != 2:
            raise forms.ValidationError('Debe tener exactamente 2 letras (ej. CO, US).')
        return value