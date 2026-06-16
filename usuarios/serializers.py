from rest_framework import serializers
from .models import Usuario, RolAcceso, Empleado

class RolAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolAcceso
        fields = '__all__'


class UsuarioSerializer(serializers.ModelSerializer):
    # source='rol_asignado.rol' asume que existe la relación inversa o propiedad en el modelo
    rol = RolAccesoSerializer(source='rol_asignado.rol', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'correo',
            'password',
            'nombre',
            'apellido',
            'telefono',
            'estado',
            'is_active',
            'is_staff',
            'is_superuser',
            'rol',
            'creado_en',
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'nombre': {'required': False},
            'apellido': {'required': False},
        }

    def create(self, validated_data):
        raw_password = validated_data.pop('password', None)
        validated_data.setdefault('nombre', '')
        validated_data.setdefault('apellido', '')
        
        usuario = Usuario(**validated_data)
        if raw_password:
            usuario.set_password(raw_password)
        else:
            usuario.set_unusable_password()
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        raw_password = validated_data.pop('password', None)
        
        # Actualización segura de atributos nativos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if raw_password:
            instance.set_password(raw_password)
            
        instance.save()
        return instance


class EmpleadoSerializer(serializers.ModelSerializer):
    # Para lectura: Retorna el objeto completo del usuario
    usuario = UsuarioSerializer(read_only=True)
    
    # Para escritura: Permite recibir el ID del usuario al crear/editar el empleado sin conflictos
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='usuario',
        write_only=True,
    )
    
    class Meta:
        model = Empleado
        fields = [
            'usuario',
            'usuario_id',
            'cargo',
            'fecha_contratacion',
            'salario_base',
            'comision_porcentaje',
            'activo',
            'creado_en',
            'actualizado_en'
        ]