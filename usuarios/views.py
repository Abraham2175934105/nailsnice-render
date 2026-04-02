from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly
from .models import Usuario, Rol, Empleado
from .serializers import UsuarioSerializer, RolSerializer, EmpleadoSerializer

class UsuarioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.usuario'

class RolViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.rol'

class EmpleadoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.empleado'
