from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from rest_framework import viewsets

# Mixins y Permisos heredados del núcleo del proyecto
from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly

# Modelos y Formularios del Módulo
from .models import Usuario, RolAcceso, Empleado
from .serializers import UsuarioSerializer, RolAccesoSerializer, EmpleadoSerializer
from .forms import UsuarioForm  # Formulario del módulo


# =========================================================================
# 1. VISTAS PARA INTERFAZ GRÁFICA (UI SERVER-RENDERED - TEMPLATES .HTML)
# =========================================================================

class UsuarioListView(LoginRequiredMixin, ListView):
    """
    Despliega el listado de usuarios en la interfaz administrativa.
    """
    model = Usuario
    template_name = 'admin/usuarios/usuario_list.html'
    context_object_name = 'usuarios'
    
    def get_queryset(self):
        # Retorna todos los usuarios mapeados desde la BD 3FN
        return Usuario.objects.all().prefetch_related('roles_asignados__id_rol')


class UsuarioCreateView(LoginRequiredMixin, CreateView):
    """
    Gestiona el formulario de creación de nuevos usuarios y asignación de rol.
    """
    model = Usuario
    form_class = UsuarioForm
    template_name = 'admin/usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Usuario creado exitosamente con su rol asignado.")
        return super().form_valid(form)


class UsuarioUpdateView(LoginRequiredMixin, UpdateView):
    """
    Gestiona la edición de usuarios existentes filtrando por su PK (id_usuario).
    """
    model = Usuario
    form_class = UsuarioForm
    template_name = 'admin/usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    pk_url_kwarg = 'id_usuario'
    
    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado correctamente.")
        return super().form_valid(form)


def alternar_estado_usuario_view(request, id_usuario):
    """
    Acción UI directa para activar/bloquear un usuario desde la tabla sin entrar al formulario.
    """
    if not request.user.is_authenticated:
        return redirect('login')
        
    usuario = get_object_or_404(Usuario, pk=id_usuario)
    
    # Verificación de seguridad básica usando las propiedades de autenticación customizadas
    user_id = getattr(request.user, 'id_usuario', None) or getattr(request.user, 'id', None)
    
    if usuario.id_usuario == user_id:
        messages.error(request, "No puedes bloquear tu propia cuenta.")
    else:
        usuario.estado = 'BLOQUEADO' if usuario.estado == 'ACTIVO' else 'ACTIVO'
        usuario.save()
        messages.success(request, f"El estado de {usuario.correo} ahora es {usuario.estado}.")
        
    return redirect('usuarios:usuario_list')


# =========================================================================
# 2. ENDPOINTS DE LA API (DJANGO REST FRAMEWORK - JSON)
# =========================================================================

class UsuarioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Usuario.objects.all().prefetch_related('roles_asignados__id_rol')
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.usuario'


class RolViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = RolAcceso.objects.all()
    serializer_class = RolAccesoSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.rol_acceso'


class EmpleadoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Empleado.objects
        .select_related('usuario')
        .prefetch_related('usuario__roles_asignados__id_rol')
    )
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'usuarios.empleado'