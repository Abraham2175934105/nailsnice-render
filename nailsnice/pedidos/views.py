from rest_framework import viewsets
from .models import Pedido, PedidoProducto, Venta, DetalleVenta, MetodoPago
from .serializers import PedidoSerializer, PedidoProductoSerializer, VentaSerializer, DetalleVentaSerializer, MetodoPagoSerializer

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

class PedidoProductoViewSet(viewsets.ModelViewSet):
    queryset = PedidoProducto.objects.all()
    serializer_class = PedidoProductoSerializer

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer

class MetodoPagoViewSet(viewsets.ModelViewSet):
    queryset = MetodoPago.objects.all()
    serializer_class = MetodoPagoSerializer