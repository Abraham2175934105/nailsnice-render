from rest_framework import serializers
from .models import Pedido, PedidoProducto, Venta, DetalleVenta, MetodoPago
from productos.models import Producto
from clientes.models import Cliente

class PedidoProductoSerializer(serializers.ModelSerializer):
    producto = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PedidoProducto
        fields = '__all__'

class PedidoSerializer(serializers.ModelSerializer):
    productos = PedidoProductoSerializer(source='pedidoproducto_set', many=True, read_only=True)
    cliente = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Pedido
        fields = '__all__'

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = '__all__'

class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(source='detalleventa_set', many=True, read_only=True)
    cliente = serializers.StringRelatedField(read_only=True)
    metodo_pago = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Venta
        fields = '__all__'

class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = '__all__'