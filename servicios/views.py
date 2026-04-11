import io

import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.auth import admin_required, employee_required
from core.permissions import IsAdminOrReadOnly
from core.pdf_reports import build_crud_pdf_response
from clientes.models import Cliente
from usuarios.models import Empleado
from .forms import AgendamientoForm, EmpleadoAgendamientoForm
from .models import Agendamiento, Servicio, TipoServicio
from .serializers import AgendamientoSerializer, ServicioSerializer, TipoServicioSerializer

AGENDAMIENTO_COLUMNS = [
    ('id', 'ID'),
    ('cliente', 'Cliente'),
    ('servicio', 'Servicio'),
    ('empleado', 'Empleado'),
    ('fecha', 'Fecha'),
    ('hora', 'Hora'),
    ('estado', 'Estado'),
    ('notas', 'Notas'),
]
AGENDAMIENTO_DEFAULT_COLUMNS = ['id', 'cliente', 'servicio', 'fecha', 'hora', 'estado']
PAGE_MIN = 10
PAGE_MAX = 30

class TipoServicioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = TipoServicio.objects.all()
    serializer_class = TipoServicioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.tipo_servicio'

class ServicioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.servicio'

class AgendamientoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Agendamiento.objects.all()
    serializer_class = AgendamientoSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.agendamiento'


def _build_agendamiento_rows(queryset, selected):
    config = {
        'id': ('ID', lambda a: a.id),
        'cliente': ('Cliente', lambda a: getattr(a.cliente.usuario, 'email', None) or str(a.cliente)),
        'servicio': ('Servicio', lambda a: a.servicio.nombre_servicio),
        'empleado': ('Empleado', lambda a: getattr(getattr(a.empleado, 'usuario', None), 'email', None) or 'Sin asignar'),
        'fecha': ('Fecha', lambda a: a.fecha_agendamiento),
        'hora': ('Hora', lambda a: a.hora_agendamiento),
        'estado': ('Estado', lambda a: a.estado_agendamiento),
        'notas': ('Notas', lambda a: a.notas or ''),
    }
    keys = [k for k in selected if k in config] or AGENDAMIENTO_DEFAULT_COLUMNS
    rows = []
    for ag in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(ag)
        rows.append(row)
    return rows


def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))


def _export_agendamientos(request, queryset, columns, fmt: str):
    rows = _build_agendamiento_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"agendamientos.{fmt}"
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
            report_title='Reporte de Agendamientos',
            rows=rows,
            filename=filename,
        )
    return None


@admin_required
def lista_agendamientos(request):
    ag_qs = Agendamiento.objects.select_related('cliente__usuario', 'servicio', 'empleado__usuario')
    search = (request.GET.get('q') or '').strip()
    if search:
        ag_qs = ag_qs.filter(
            Q(cliente__usuario__nombre1__icontains=search)
            | Q(cliente__usuario__apellido1__icontains=search)
            | Q(cliente__usuario__email__icontains=search)
            | Q(servicio__nombre_servicio__icontains=search)
            | Q(empleado__usuario__email__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(ag_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(AGENDAMIENTO_COLUMNS)] or AGENDAMIENTO_DEFAULT_COLUMNS
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
            export_source = ag_qs
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_agendamientos(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'agendamientos/agendamientos.html', {
        'page_obj': page_obj,
        'agendamientos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': AGENDAMIENTO_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
    })


@admin_required
def crear_agendamiento(request):
    if request.method == 'POST':
        form = AgendamientoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_agendamientos')
    else:
        form = AgendamientoForm()
    return render(request, 'agendamientos/formulario.html', {'form': form})


@admin_required
def editar_agendamiento(request, id):
    agendamiento = get_object_or_404(Agendamiento, id=id)
    if request.method == 'POST':
        form = AgendamientoForm(request.POST, instance=agendamiento)
        if form.is_valid():
            form.save()
            return redirect('lista_agendamientos')
    else:
        form = AgendamientoForm(instance=agendamiento)
    return render(request, 'agendamientos/formulario.html', {'form': form})


@admin_required
def eliminar_agendamiento(request, id):
    agendamiento = get_object_or_404(Agendamiento, id=id)
    agendamiento.delete()
    return redirect('lista_agendamientos')


def _get_or_create_employee_for_user(user):
    empleado, _ = Empleado.objects.get_or_create(usuario=user)
    return empleado


@employee_required
def empleado_lista_agendamientos(request):
    empleado = _get_or_create_employee_for_user(request.user)
    ag_qs = (
        Agendamiento.objects
        .select_related('cliente__usuario', 'servicio', 'empleado__usuario')
        .filter(empleado=empleado)
    )

    search = (request.GET.get('q') or '').strip()
    if search:
        ag_qs = ag_qs.filter(
            Q(cliente__usuario__nombre1__icontains=search)
            | Q(cliente__usuario__apellido1__icontains=search)
            | Q(cliente__usuario__email__icontains=search)
            | Q(servicio__nombre_servicio__icontains=search)
            | Q(estado_agendamiento__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(ag_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'empleado/agendamientos.html', {
        'page_obj': page_obj,
        'agendamientos': page_obj.object_list,
        'search': search,
        'page_size': page_size,
    })


@employee_required
def empleado_crear_agendamiento(request):
    empleado = _get_or_create_employee_for_user(request.user)
    if request.method == 'POST':
        form = EmpleadoAgendamientoForm(request.POST)
        form.instance.empleado = empleado
        if form.is_valid():
            form.save()
            messages.success(request, 'Agendamiento registrado correctamente.')
            return redirect('empleado_agendamientos')
        messages.error(request, 'Corrige los errores del formulario para guardar el agendamiento.')
    else:
        form = EmpleadoAgendamientoForm()

    return render(request, 'empleado/agendamiento_form.html', {
        'form': form,
        'is_edit': False,
    })


@employee_required
def empleado_editar_agendamiento(request, id):
    empleado = _get_or_create_employee_for_user(request.user)
    agendamiento = get_object_or_404(Agendamiento, id=id, empleado=empleado)
    if request.method == 'POST':
        form = EmpleadoAgendamientoForm(request.POST, instance=agendamiento)
        form.instance.empleado = empleado
        if form.is_valid():
            form.save()
            messages.success(request, 'Agendamiento actualizado correctamente.')
            return redirect('empleado_agendamientos')
        messages.error(request, 'Corrige los errores del formulario para actualizar el agendamiento.')
    else:
        form = EmpleadoAgendamientoForm(instance=agendamiento)

    return render(request, 'empleado/agendamiento_form.html', {
        'form': form,
        'is_edit': True,
        'agendamiento': agendamiento,
    })


@employee_required
def empleado_eliminar_agendamiento(request, id):
    empleado = _get_or_create_employee_for_user(request.user)
    agendamiento = get_object_or_404(Agendamiento, id=id, empleado=empleado)
    agendamiento.delete()
    messages.info(request, 'Agendamiento eliminado.')
    return redirect('empleado_agendamientos')


@admin_required
def carga_masiva_agendamientos(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Debes adjuntar un archivo CSV o Excel.')
            return redirect('agendamientos_carga_masiva')

        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception:
            messages.error(request, 'No se pudo leer el archivo. Usa CSV o Excel válido.')
            return redirect('agendamientos_carga_masiva')

        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {'cliente_email', 'servicio', 'fecha', 'hora'}
        alt_required = {'cliente_email', 'servicio', 'fecha_agendamiento', 'hora_agendamiento'}
        if not required.issubset(df.columns) and not alt_required.issubset(df.columns):
            messages.error(request, 'Faltan columnas requeridas: cliente_email, servicio, fecha, hora.')
            return redirect('agendamientos_carga_masiva')

        creados = 0
        errores = []
        valid_estados = {choice[0] for choice in Agendamiento.ESTADO_CHOICES}

        for idx, row in df.iterrows():
            try:
                cliente_email = str(row.get('cliente_email') or '').strip()
                servicio_nombre = str(row.get('servicio') or row.get('servicio_nombre') or '').strip()
                fecha_raw = row.get('fecha') if 'fecha' in df.columns else row.get('fecha_agendamiento')
                hora_raw = row.get('hora') if 'hora' in df.columns else row.get('hora_agendamiento')
                empleado_email = str(row.get('empleado_email') or '').strip()
                estado_val = str(row.get('estado') or row.get('estado_agendamiento') or 'Pendiente').strip()
                notas_val = str(row.get('notas') or '').strip()

                if not cliente_email or not servicio_nombre or pd.isna(fecha_raw) or pd.isna(hora_raw):
                    raise ValueError('Datos faltantes: cliente_email, servicio, fecha u hora.')

                try:
                    fecha_val = pd.to_datetime(fecha_raw).date()
                except Exception:
                    raise ValueError('Fecha inválida')

                try:
                    hora_val = pd.to_datetime(str(hora_raw)).time()
                except Exception:
                    raise ValueError('Hora inválida')

                try:
                    cliente_obj = Cliente.objects.select_related('usuario').get(usuario__email__iexact=cliente_email)
                except Cliente.DoesNotExist:
                    raise ValueError('Cliente no encontrado')

                servicio_obj = Servicio.objects.filter(nombre_servicio__iexact=servicio_nombre).first()
                if not servicio_obj:
                    raise ValueError('Servicio no encontrado')

                empleado_obj = None
                if empleado_email:
                    empleado_obj = Empleado.objects.filter(usuario__email__iexact=empleado_email).first()
                    if not empleado_obj:
                        raise ValueError('Empleado no encontrado')

                estado_clean = next((choice for choice in valid_estados if choice.lower() == estado_val.lower()), 'Pendiente')

                nuevo = Agendamiento(
                    cliente=cliente_obj,
                    servicio=servicio_obj,
                    empleado=empleado_obj,
                    fecha_agendamiento=fecha_val,
                    hora_agendamiento=hora_val,
                    estado_agendamiento=estado_clean,
                    notas=notas_val,
                )
                nuevo.full_clean()
                nuevo.save()
                creados += 1
            except Exception as exc:
                errores.append(f'Fila {idx + 1}: {exc}')

        if errores:
            messages.warning(request, f'Creados {creados}. Errores en {len(errores)} filas.')
        else:
            messages.success(request, f'Cargados {creados} agendamientos correctamente.')
        return redirect('lista_agendamientos')

    return render(request, 'agendamientos/carga_masiva.html')
