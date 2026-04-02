from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOrReadOnly
from .models import ProductoMaquillaje
from .serializers import ProductoMaquillajeSerializer


class ProductoMaquillajeViewSet(AuditViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ProductoMaquillaje.activos.all()
    serializer_class = ProductoMaquillajeSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'inventario.api'
