from rest_framework import serializers
from .models import TipoServicio, Servicio, Agendamiento
from clientes.models import Cliente
from usuarios.models import Empleado

class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = '__all__'

class ServicioSerializer(serializers.ModelSerializer):
    tipo_servicio = TipoServicioSerializer(read_only=True)
    
    class Meta:
        model = Servicio
        fields = '__all__'

class AgendamientoSerializer(serializers.ModelSerializer):
    cliente = serializers.StringRelatedField(read_only=True)
    empleado = serializers.StringRelatedField(read_only=True)
    servicio = ServicioSerializer(read_only=True)
    
    class Meta:
        model = Agendamiento
        fields = '__all__'