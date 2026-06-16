from rest_framework import viewsets
from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOrReadOnly
from .models import Bodega, SaldoInventario, MovimientoInventario
# Importamos los nuevos serializadores (asegúrate de que existan en serializers.py)
from .serializers import BodegaSerializer, SaldoInventarioSerializer

class BodegaViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Bodega.objects.filter(activo=True)
    serializer_class = BodegaSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'inventario.bodega'

class SaldoInventarioViewSet(AuditViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver las existencias actuales de productos (Variantes).
    """
    queryset = SaldoInventario.objects.all()
    serializer_class = SaldoInventarioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'inventario.saldo'