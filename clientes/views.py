from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly

from .forms import ClienteForm, DireccionUsuarioForm
from .models import (
    Cliente,
    CuentaFidelizacion,
    DireccionUsuario,
    MetodoPagoCliente,
    LibroPuntos,  # Importación requerida para la consulta tipada
)
from .serializers import (
    ClienteSerializer,
    CuentaFidelizacionSerializer,
    DireccionUsuarioSerializer,
    MetodoPagoClienteSerializer,
)


# ===========================================================================
# API REST — ViewSets
# ===========================================================================

class ClienteViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de clientes (perfil_cliente + usuario).
    Extiende tu ViewSet original añadiendo select_related y tres
    actions de detalle para direcciones, métodos de pago y fidelización.
    """
    queryset = Cliente.objects.select_related('usuario').all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'clientes.cliente'

    @action(detail=True, methods=['get'], url_path='direcciones')
    def direcciones(self, request, pk=None):
        """GET /api/clientes/{pk}/direcciones/"""
        cliente = self.get_object()
        qs = DireccionUsuario.objects.filter(usuario=cliente.usuario)
        return Response(DireccionUsuarioSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='metodos-pago')
    def metodos_pago(self, request, pk=None):
        """GET /api/clientes/{pk}/metodos-pago/"""
        cliente = self.get_object()
        qs = MetodoPagoCliente.objects.filter(cliente=cliente).select_related(
            'tipo_metodo', 'proveedor'
        )
        return Response(MetodoPagoClienteSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='fidelizacion')
    def fidelizacion(self, request, pk=None):
        """GET /api/clientes/{pk}/fidelizacion/"""
        cliente = self.get_object()
        cuenta = get_object_or_404(CuentaFidelizacion, cliente=cliente)
        return Response(CuentaFidelizacionSerializer(cuenta).data)


class DireccionUsuarioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD de direcciones.
    Filtra por ?usuario=<id> para obtener solo las de un cliente.
    """
    queryset = DireccionUsuario.objects.select_related('usuario').all()
    serializer_class = DireccionUsuarioSerializer
    permission_classes = [IsAdminOnly]
    audit_prefix = 'clientes.direccion'
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        usuario_id = self.request.query_params.get('usuario')
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        return qs


class MetodoPagoClienteViewSet(
    AuditViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Solo lectura — los tokens los gestiona la pasarela de pago.
    Filtra por ?cliente=<id> para obtener los métodos de un cliente.
    """
    queryset = MetodoPagoCliente.objects.select_related(
        'tipo_metodo', 'proveedor', 'cliente'
    ).all()
    serializer_class = MetodoPagoClienteSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        cliente_id = self.request.query_params.get('cliente')
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        return qs


# ===========================================================================
# Vistas web — Templates HTML
# ===========================================================================

@login_required
def cliente_list(request):
    """Lista de todos los clientes con búsqueda y filtros."""
    clientes = Cliente.objects.select_related('usuario').all()

    search = (request.GET.get('q') or '').strip()
    if search:
        from django.db.models import Q
        clientes = clientes.filter(
            Q(usuario__correo__icontains=search)
            | Q(usuario__nombre__icontains=search)
            | Q(usuario__apellido__icontains=search)
            | Q(usuario__telefono__icontains=search)
        )

    fidelizacion = (request.GET.get('fidelizacion') or '').strip().lower()
    if fidelizacion == 'activa':
        clientes = clientes.filter(acepta_fidelizacion=True)
    elif fidelizacion == 'inactiva':
        clientes = clientes.filter(acepta_fidelizacion=False)

    orden = (request.GET.get('orden') or 'recientes').strip().lower()
    if orden == 'nombre_asc':
        clientes = clientes.order_by('usuario__nombre', 'usuario__apellido')
    elif orden == 'nombre_desc':
        clientes = clientes.order_by('-usuario__nombre', '-usuario__apellido')
    else:
        clientes = clientes.order_by('-creado_en')

    return render(request, 'clientes/cliente_list.html', {
        'clientes': clientes,
        'search': search,
        'fidelizacion_selected': fidelizacion,
        'orden_selected': orden,
    })


@login_required
def cliente_detail(request, pk):
    """
    Detalle del cliente con tabs:
    perfil | direcciones | métodos de pago | fidelización.
    """
    cliente = get_object_or_404(
        Cliente.objects.select_related('usuario'), pk=pk
    )

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('clientes:cliente_detail', pk=pk)
    else:
        form = ClienteForm(instance=cliente)

    direcciones = DireccionUsuario.objects.filter(usuario=cliente.usuario)
    metodos_pago = MetodoPagoCliente.objects.filter(cliente=cliente).select_related(
        'tipo_metodo', 'proveedor'
    )
    cuenta_fidelizacion = getattr(cliente, 'cuenta_fidelizacion', None)
    
    # CORRECCIÓN: Usamos la consulta directa sobre el modelo LibroPuntos filtrando 
    # por la FK de cliente para evitar atributos dinámicos desconocidos por Pylance
    movimientos = (
        LibroPuntos.objects.filter(cuenta__cliente=cliente).select_related('creado_por').all()[:50]
        if cuenta_fidelizacion else []
    )

    return render(request, 'clientes/cliente_detail.html', {
        'cliente': cliente,
        'form': form,
        'direcciones': direcciones,
        'metodos_pago': metodos_pago,
        'cuenta_fidelizacion': cuenta_fidelizacion,
        'movimientos': movimientos,
    })


@login_required
def cliente_create(request):
    """Crea un nuevo cliente (usuario + perfil_cliente)."""
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente creado correctamente.')
            return redirect('clientes:cliente_list')
    else:
        form = ClienteForm()
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'accion': 'Crear',
    })


@login_required
def direccion_create(request, cliente_pk):
    """Agrega una nueva dirección al cliente."""
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    if request.method == 'POST':
        form = DireccionUsuarioForm(request.POST)
        if form.is_valid():
            direccion = form.save(commit=False)
            direccion.usuario = cliente.usuario
            direccion.save()
            messages.success(request, 'Dirección agregada correctamente.')
            return redirect('clientes:cliente_detail', pk=cliente_pk)
    else:
        form = DireccionUsuarioForm()
    return render(request, 'clientes/direccion_form.html', {
        'form': form,
        'cliente': cliente,
        'accion': 'Agregar',
    })


@login_required
def direccion_update(request, cliente_pk, pk):
    """Edita una dirección existente."""
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    direccion = get_object_or_404(DireccionUsuario, pk=pk, usuario=cliente.usuario)
    if request.method == 'POST':
        form = DireccionUsuarioForm(request.POST, instance=direccion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dirección actualizada.')
            return redirect('clientes:cliente_detail', pk=cliente_pk)
    else:
        form = DireccionUsuarioForm(instance=direccion)
    return render(request, 'clientes/direccion_form.html', {
        'form': form,
        'cliente': cliente,
        'accion': 'Editar',
    })


@login_required
def direccion_delete(request, cliente_pk, pk):
    """Elimina una dirección (solo acepta POST para evitar borrados accidentales)."""
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    direccion = get_object_or_404(DireccionUsuario, pk=pk, usuario=cliente.usuario)
    if request.method == 'POST':
        direccion.delete()
        messages.success(request, 'Dirección eliminada.')
    return redirect('clientes:cliente_detail', pk=cliente_pk)