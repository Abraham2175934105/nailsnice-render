from decimal import Decimal
from rest_framework import serializers
from .models import CarritoCompra, ItemCarritoCompra, PedidoVenta, DetallePedidoVenta, TransaccionPago, HistorialEstadoPedido
from productos.serializers import ProductoSerializer  # Opcional para nesting si se requiere en el futuro

# ---------------------------------------------------------------------------
# 1. Serializadores del Carrito de Compras
# ---------------------------------------------------------------------------

class ItemCarritoCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCarritoCompra
        fields = [
            'id_item_carrito',
            'carrito',
            'variante',
            'cantidad',
            'precio_unitario_snapshot',
            'creado_en',
            'actualizado_en'
        ]
        read_only_fields = ['id_item_carrito', 'creado_en', 'actualizado_en']


class CarritoCompraSerializer(serializers.ModelSerializer):
    items = ItemCarritoCompraSerializer(many=True, read_only=True)

    class Meta:
        model = CarritoCompra
        fields = [
            'id_carrito',
            'cliente',
            'estado',
            'id_cliente_activo',
            'codigo_moneda',
            'expira_en',
            'items',
            'creado_en',
            'actualizado_en'
        ]
        read_only_fields = ['id_carrito', 'creado_en', 'actualizado_en']


# ---------------------------------------------------------------------------
# 2. Serializadores del Pedido de Venta
# ---------------------------------------------------------------------------

class DetallePedidoVentaSerializer(serializers.ModelSerializer):
    subtotal_linea = serializers.ReadOnlyField(source='subtotal')

    class Meta:
        model = DetallePedidoVenta
        fields = [
            'id_detalle_pedido',
            'pedido',
            'variante',
            'nombre_producto_snapshot',
            'sku_snapshot',
            'cantidad',
            'precio_unitario',
            'total_linea',
            'subtotal_linea',
            'creado_en'
        ]
        read_only_fields = ['id_detalle_pedido', 'total_linea', 'creado_en']


class PedidoVentaSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoVentaSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = PedidoVenta
        fields = [
            'id_pedido',
            'numero_pedido',
            'cliente',
            'carrito',
            'estado',
            'estado_display',
            'subtotal',
            'monto_envio',
            'monto_impuesto',
            'monto_descuento',
            'monto_total',
            'puntos_ganados',
            'puntos_redimidos',
            'direccion_envio',
            'direccion_factura',
            'detalles',
            'realizado_en',
            'creado_en',
            'actualizado_en'
        ]
        read_only_fields = ['id_pedido', 'numero_pedido', 'realizado_en', 'creado_en', 'actualizado_en']

    def validate(self, attrs):
        """Validación estricta de coherencia matemática de los montos Decimales."""
        subtotal = attrs.get('subtotal', Decimal('0.00'))
        envio = attrs.get('monto_envio', Decimal('0.00'))
        impuesto = attrs.get('monto_impuesto', Decimal('0.00'))
        descuento = attrs.get('monto_descuento', Decimal('0.00'))
        monto_total = attrs.get('monto_total', Decimal('0.00'))

        calculado = subtotal + envio + impuesto - descuento
        if abs(monto_total - calculado) > Decimal('0.01'):
            raise serializers.ValidationError({
                "monto_total": f"El monto total ({monto_total}) no coincide con el cálculo matemático ({calculado})."
            })
        return attrs


# ---------------------------------------------------------------------------
# 3. Historial y Transacciones de Pago
# ---------------------------------------------------------------------------

class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialEstadoPedido
        fields = '__all__'


class TransaccionPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransaccionPago
        fields = '__all__'
        read_only_fields = ['id_transaccion', 'creado_en', 'actualizado_en']