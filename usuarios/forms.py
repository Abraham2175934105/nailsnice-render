from django import forms
from django.contrib.auth.hashers import make_password
from .models import Usuario, RolAcceso, UsuarioRol

class UsuarioForm(forms.ModelForm):
    # Campo inyectado para solventar la relación N:M desde un solo formulario
    rol = forms.ModelChoiceField(
        queryset=RolAcceso.objects.all(),
        required=True,
        label="Rol de Acceso",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Campo de contraseña explícito para el alta de usuarios
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        required=False,
        label="Contraseña"
    )

    class Meta:
        model = Usuario
        fields = ['correo', 'password', 'nombre', 'apellido', 'telefono', 'estado']
        widgets = {
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@nailsnice.com'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(choices=[('ACTIVO', 'Activo'), ('BLOQUEADO', 'Bloqueado')], attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando un usuario existente, pre-poblamos el selector de rol
        if self.instance and self.instance.pk:
            rol_actual = self.instance.rol_principal
            if rol_actual:
                # Modificación para apuntar al objeto o ID correcto según tu helper
                self.fields['rol'].initial = rol_actual
            # Si se edita, la contraseña no es obligatoria
            self.fields['password'].required = False
            self.fields['password'].help_text = "Dejar en blanco si no se desea cambiar la contraseña."
        else:
            # Si es un usuario nuevo, la contraseña SÍ es obligatoria
            self.fields['password'].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        
        # Si se proporcionó una contraseña (nueva o cambiada), se encripta
        if self.cleaned_data.get('password'):
            usuario.password = make_password(self.cleaned_data['password'])
        
        if commit:
            usuario.save()
            rol_seleccionado = self.cleaned_data.get('rol')
            # Eliminar asignaciones viejas para mantener consistencia estricta
            UsuarioRol.objects.filter(id_usuario=usuario).delete()
            # Crear nueva asignación según la BD 3FN
            UsuarioRol.objects.create(id_usuario=usuario, id_rol=rol_seleccionado)
            
        return usuario