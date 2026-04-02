from rest_framework import serializers
from .models import Usuario, Rol, Empleado

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'first_name', 'last_name', 'rol', 'is_active', 'date_joined']
        extra_kwargs = {'password': {'write_only': True}}

class EmpleadoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    
    class Meta:
        model = Empleado
        fields = '__all__'