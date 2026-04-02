from rest_framework import serializers
from .models import Cliente, ServicioCliente
from usuarios.models import Usuario

class ClienteSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Cliente
        fields = '__all__'

class ServicioClienteSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    
    class Meta:
        model = ServicioCliente
        fields = '__all__'