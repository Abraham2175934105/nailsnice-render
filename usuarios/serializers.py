from rest_framework import serializers
from .models import Usuario, Rol, Empleado

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(source='id_rol', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'password', 'nombre1', 'nombre2', 'apellido1', 'apellido2', 'telefono', 'estado_usuario', 'id_rol', 'rol', 'is_active', 'creado_en']
        extra_kwargs = {'password': {'write_only': True}}

class EmpleadoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = Empleado
        fields = '__all__'