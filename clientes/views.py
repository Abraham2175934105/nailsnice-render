from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
import io
import pandas as pd
from django.core.paginator import Paginator
from django.http import HttpResponse
from core.pdf_reports import build_crud_pdf_response
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

CLIENTE_COLUMNS = [
    ('nombre', 'Nombre'),
    ('apellido', 'Apellido'),
    ('correo', 'Correo'),
    ('telefono', 'Teléfono'),
    ('fidelizacion', 'Fidelización'),
    ('creado_en', 'Fecha Registro'),
]
CLIENTE_DEFAULT_COLUMNS = ['nombre', 'apellido', 'correo', 'telefono', 'fidelizacion', 'creado_en']
PAGE_MIN = 10
PAGE_MAX = 30

def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))

def _build_cliente_rows(queryset, selected):
    config = {
        'nombre': ('Nombre', lambda c: c.usuario.nombre),
        'apellido': ('Apellido', lambda c: c.usuario.apellido),
        'correo': ('Correo', lambda c: c.usuario.correo),
        'telefono': ('Teléfono', lambda c: c.usuario.telefono or 'No registrado'),
        'fidelizacion': ('Fidelización', lambda c: 'Activa' if c.acepta_fidelizacion else 'Inactiva'),
        'creado_en': ('Fecha Registro', lambda c: c.creado_en),
    }
    keys = [k for k in selected if k in config] or CLIENTE_DEFAULT_COLUMNS
    rows = []
    for cliente in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(cliente)
        rows.append(row)
    return rows

def _export_clientes(request, queryset, columns, fmt: str):
    rows = _build_cliente_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"clientes.{fmt}"
    if fmt == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return HttpResponse(buffer.getvalue(), content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'xlsx':
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'pdf':
        return build_crud_pdf_response(
            request=request,
            report_title='Reporte de Clientes',
            rows=rows,
            filename=filename,
        )
    return None

@login_required
def cliente_list(request):
    """Lista de todos los clientes con búsqueda y filtros."""
    clientes_qs = Cliente.objects.filter(
        usuario__roles_asignados__id_rol__nombre='Cliente'
    ).select_related('usuario').all()

    search = (request.GET.get('q') or '').strip()
    if search:
        from django.db.models import Q
        clientes_qs = clientes_qs.filter(
            Q(usuario__correo__icontains=search)
            | Q(usuario__nombre__icontains=search)
            | Q(usuario__apellido__icontains=search)
            | Q(usuario__telefono__icontains=search)
        )

    fidelizacion = (request.GET.get('fidelizacion') or '').strip().lower()
    if fidelizacion == 'activa':
        clientes_qs = clientes_qs.filter(acepta_fidelizacion=True)
    elif fidelizacion == 'inactiva':
        clientes_qs = clientes_qs.filter(acepta_fidelizacion=False)

    orden = (request.GET.get('orden') or 'recientes').strip().lower()
    if orden == 'nombre_asc':
        clientes_qs = clientes_qs.order_by('usuario__nombre', 'usuario__apellido')
    elif orden == 'nombre_desc':
        clientes_qs = clientes_qs.order_by('-usuario__nombre', '-usuario__apellido')
    else:
        clientes_qs = clientes_qs.order_by('-creado_en')

    # Pagination
    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(clientes_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(CLIENTE_COLUMNS)] or CLIENTE_DEFAULT_COLUMNS
    export_scope = (request.GET.get('export_scope') or 'page').lower()
    if export_scope not in {'page', 'pages', 'all'}:
        export_scope = 'page'

    try:
        export_page = int(request.GET.get('export_page') or page_obj.number)
    except (TypeError, ValueError):
        export_page = page_obj.number
    export_page = max(1, min(export_page, paginator.num_pages or 1))

    export_pages = []
    for raw_page in request.GET.getlist('export_pages'):
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if 1 <= page_num <= (paginator.num_pages or 1):
            export_pages.append(page_num)
    export_pages = sorted(set(export_pages)) or [export_page]

    export_fmt = (request.GET.get('export') or '').lower()
    if export_fmt in {'csv', 'xlsx', 'pdf'}:
        if export_scope == 'all':
            export_source = clientes_qs
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_clientes(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'clientes/cliente_list.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
        'search': search,
        'fidelizacion_selected': fidelizacion,
        'orden_selected': orden,
        'page_size': page_size,
        'columns_options': CLIENTE_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
        'total_registros': paginator.count,
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