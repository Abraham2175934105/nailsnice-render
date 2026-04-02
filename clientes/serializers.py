from rest_framework import serializers
from .models import Cliente, ServicioCliente
from usuarios.models import Usuario, Rol
from usuarios.serializers import UsuarioSerializer

class ClienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    
    class Meta:
        model = Cliente
        fields = '__all__'
    
    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        password = usuario_data.pop('password', None)
        # Set rol to Cliente if not provided
        if 'id_rol' not in usuario_data:
            rol_cliente, _ = Rol.objects.get_or_create(nombre='Cliente')
            usuario_data['id_rol'] = rol_cliente
            
        # Usamos el manager para crear el usuario correctamente con password hasheado
        usuario = Usuario.objects.create_user(password=password, **usuario_data)
        
        cliente = Cliente.objects.create(usuario=usuario, **validated_data)
        return cliente

class ServicioClienteSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    
    class Meta:
        model = ServicioCliente
        fields = '__all__'