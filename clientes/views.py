from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly
from .models import Cliente, ServicioCliente
from .serializers import ClienteSerializer, ServicioClienteSerializer

class ClienteViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'clientes.cliente'

class ServicioClienteViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = ServicioCliente.objects.all()
    serializer_class = ServicioClienteSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'clientes.servicio_cliente'
