import io

import pandas as pd  # type: ignore
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets

from core.audit import AuditViewSetMixin
from core.auth import admin_required, employee_required
from django.contrib.auth.decorators import login_required
from core.permissions import IsAdminOrReadOnly
from core.pdf_reports import build_crud_pdf_response
from clientes.models import Cliente
from usuarios.models import Empleado
from .forms import (
    AgendamientoForm, EmpleadoAgendamientoForm, ClienteAgendamientoForm,
    ServicioForm, CategoriaServicioForm, TipoServicioForm, EmpleadoServicioForm
)
from .models import (
    Agendamiento, Servicio, TipoServicio, 
    CategoriaServicio, EmpleadoServicio, HistorialEstadoAgendamiento
)
from .serializers import (
    AgendamientoSerializer, ServicioSerializer, TipoServicioSerializer,
    CategoriaServicioSerializer, EmpleadoServicioSerializer, HistorialEstadoAgendamientoSerializer
)

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

class CategoriaServicioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = CategoriaServicio.objects.all()
    serializer_class = CategoriaServicioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.categoria_servicio'

class ServicioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.servicio'

class EmpleadoServicioViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = EmpleadoServicio.objects.all()
    serializer_class = EmpleadoServicioSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.empleado_servicio'

class AgendamientoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = Agendamiento.objects.all()
    serializer_class = AgendamientoSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.agendamiento'

class HistorialEstadoAgendamientoViewSet(AuditViewSetMixin, viewsets.ModelViewSet):
    queryset = HistorialEstadoAgendamiento.objects.all()
    serializer_class = HistorialEstadoAgendamientoSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = 'servicios.historial_estado_agendamiento'


def _build_agendamiento_rows(queryset, selected):
    config = {
        'id': ('ID', lambda a: a.id_agendamiento),
        'cliente': ('Cliente', lambda a: getattr(a.cliente.usuario, 'correo', None) or str(a.cliente)),
        'servicio': ('Servicio', lambda a: a.servicio.nombre),
        'empleado': ('Empleado', lambda a: getattr(getattr(a.empleado, 'usuario', None), 'correo', None) or 'Sin asignar'),
        'fecha': ('Fecha', lambda a: a.inicia_en.date() if a.inicia_en else None),
        'hora': ('Hora', lambda a: a.inicia_en.time() if a.inicia_en else None),
        'estado': ('Estado', lambda a: a.estado),
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
            Q(cliente__usuario__nombre__icontains=search)
            | Q(cliente__usuario__apellido__icontains=search)
            | Q(cliente__usuario__correo__icontains=search)
            | Q(servicio__nombre__icontains=search)
            | Q(empleado__usuario__correo__icontains=search)
            | Q(estado__icontains=search)
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


# ========== AGENDAMIENTOS CLIENTE ==========

def _get_or_create_client_for_user(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return None
    try:
        cliente, _ = Cliente.objects.get_or_create(usuario=user)
        return cliente
    except Exception:
        return None

@login_required
def cliente_crear_agendamiento(request):
    cliente = _get_or_create_client_for_user(request.user)
        
    if request.method == 'POST':
        form = ClienteAgendamientoForm(request.POST)
        if cliente:
            form.instance.cliente = cliente
        form.instance.estado = 'PENDIENTE'
        form.instance.canal = 'WEB'
        if form.is_valid():
            if not cliente:
                messages.error(request, 'Error: Perfil de cliente no disponible. Por favor contacta soporte.')
                return redirect('/')
            cita = form.save(commit=False)
            cita.cliente = cliente
            cita.save()
            messages.success(request, '¡Tu cita ha sido agendada con éxito! Te esperamos.')
            return redirect('/')
        messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ClienteAgendamientoForm()

    # Prevenir 500 si falta el usuario o tiene atributos nulos
    try:
        user_data = {
            'nombre': request.user.nombre if hasattr(request.user, 'nombre') else '',
            'apellido': request.user.apellido if hasattr(request.user, 'apellido') else '',
            'correo': request.user.correo if hasattr(request.user, 'correo') else getattr(request.user, 'email', ''),
        }
    except Exception:
        user_data = {'nombre': '', 'apellido': '', 'correo': ''}

    try:
        return render(request, 'agendamientos/agendar_cliente.html', {
            'form': form,
            'user_data': user_data,
        })
    except Exception as e:
        import logging
        logging.error(f"Error renderizando agendar_cliente.html: {str(e)}")
        from django.http import HttpResponseServerError
        return HttpResponseServerError(
            f"<h1>Error Crítico de Renderizado</h1>"
            f"<p>El sistema experimentó un fallo al generar la vista. Asegúrese de que todas las plantillas base existan.</p>"
            f"<p><strong>Detalle técnico:</strong> {str(e)}</p>"
        )


# ========== AGENDAMIENTOS ADMIN ==========

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
    agendamiento = get_object_or_404(Agendamiento, pk=id)
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
    agendamiento = get_object_or_404(Agendamiento, pk=id)
    agendamiento.delete()
    return redirect('lista_agendamientos')


def _get_or_create_employee_for_user(user):
    empleado, _ = Empleado.objects.get_or_create(
        usuario=user,
        defaults={
            'codigo_empleado': f"EMP-{getattr(user, 'id_usuario', getattr(user, 'id', 0))}",
            'cargo': 'Empleado Generado'
        }
    )
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
            Q(cliente__usuario__nombre__icontains=search)
            | Q(cliente__usuario__apellido__icontains=search)
            | Q(cliente__usuario__correo__icontains=search)
            | Q(servicio__nombre__icontains=search)
            | Q(estado__icontains=search)
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
    agendamiento = get_object_or_404(Agendamiento, pk=id, empleado=empleado)
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
    agendamiento = get_object_or_404(Agendamiento, pk=id, empleado=empleado)
    agendamiento.delete()
    messages.info(request, 'Agendamiento eliminado.')
    return redirect('empleado_agendamientos')


# ========== SERVICIOS CRUD ==========

@admin_required
def lista_servicios(request):
    servicios_qs = Servicio.objects.select_related('tipo_servicio', 'categoria_servicio')
    
    search = (request.GET.get('q') or '').strip()
    if search:
        servicios_qs = servicios_qs.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(tipo_servicio__nombre__icontains=search) |
            Q(categoria_servicio__nombre__icontains=search)
        )
    
    filtro_tipo = request.GET.get('tipo')
    if filtro_tipo:
        servicios_qs = servicios_qs.filter(tipo_servicio_id=filtro_tipo)
    
    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(servicios_qs, page_size)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    tipos = TipoServicio.objects.all()
    
    return render(request, 'servicios/lista_servicios.html', {
        'page_obj': page_obj,
        'servicios': page_obj.object_list,
        'search': search,
        'tipos': tipos,
        'filtro_tipo': filtro_tipo,
    })


@admin_required
def crear_servicio(request):
    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio creado correctamente.')
            return redirect('lista_servicios')
        messages.error(request, 'Error al crear el servicio. Revisa los datos.')
    else:
        form = ServicioForm()
    
    return render(request, 'servicios/servicio_form.html', {
        'form': form,
        'titulo': 'Crear Servicio',
        'es_crear': True,
    })


@admin_required
def editar_servicio(request, id):
    servicio = get_object_or_404(Servicio, pk=id)
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio actualizado correctamente.')
            return redirect('lista_servicios')
        messages.error(request, 'Error al actualizar. Revisa los datos.')
    else:
        form = ServicioForm(instance=servicio)
    
    return render(request, 'servicios/servicio_form.html', {
        'form': form,
        'titulo': f'Editar: {servicio.nombre}',
        'es_crear': False,
        'servicio': servicio,
    })


@admin_required
def eliminar_servicio(request, id):
    servicio = get_object_or_404(Servicio, pk=id)
    nombre = servicio.nombre
    servicio.delete()
    messages.info(request, f'Servicio "{nombre}" eliminado.')
    return redirect('lista_servicios')




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
        required = {'cliente_correo', 'servicio', 'fecha', 'hora'}
        alt_required = {'cliente_email', 'servicio', 'fecha_agendamiento', 'hora_agendamiento'}
        if not required.issubset(df.columns) and not alt_required.issubset(df.columns):
            messages.error(request, 'Faltan columnas requeridas: cliente_correo/cliente_email, servicio, fecha, hora.')
            return redirect('agendamientos_carga_masiva')

        creados = 0
        errores = []
        valid_estados = {choice[0] for choice in Agendamiento.ESTADO_CHOICES}

        for idx, row in df.iterrows():
            try:
                cliente_correo = str(row.get('cliente_correo') or row.get('cliente_email') or '').strip()
                servicio_nombre = str(row.get('servicio') or row.get('servicio_nombre') or '').strip()
                fecha_raw = row.get('fecha') if 'fecha' in df.columns else row.get('fecha_agendamiento')
                hora_raw = row.get('hora') if 'hora' in df.columns else row.get('hora_agendamiento')
                empleado_correo = str(row.get('empleado_correo') or row.get('empleado_email') or '').strip()
                estado_val = str(row.get('estado') or row.get('estado_agendamiento') or 'PENDIENTE').strip()
                notas_val = str(row.get('notas') or '').strip()

                if not cliente_correo or not servicio_nombre or pd.isna(fecha_raw) or pd.isna(hora_raw):
                    raise ValueError('Datos faltantes: cliente_correo/cliente_email, servicio, fecha u hora.')

                try:
                    fecha_val = pd.to_datetime(fecha_raw).date()
                except Exception:
                    raise ValueError('Fecha inválida')

                try:
                    hora_val = pd.to_datetime(str(hora_raw)).time()
                except Exception:
                    raise ValueError('Hora inválida')

                try:
                    cliente_obj = Cliente.objects.select_related('usuario').get(usuario__correo__iexact=cliente_correo)
                except Cliente.DoesNotExist:
                    raise ValueError('Cliente no encontrado')

                servicio_obj = Servicio.objects.filter(nombre__iexact=servicio_nombre).first()
                if not servicio_obj:
                    raise ValueError('Servicio no encontrado')

                empleado_obj = None
                if empleado_correo:
                    empleado_obj = Empleado.objects.filter(usuario__correo__iexact=empleado_correo).first()
                    if not empleado_obj:
                        raise ValueError('Empleado no encontrado')

                estado_clean = next((choice for choice in valid_estados if choice.lower() == estado_val.lower()), 'PENDIENTE')

                inicia_en = pd.to_datetime(f"{fecha_val} {hora_val}")
                termina_en = inicia_en + pd.to_timedelta(int(servicio_obj.duracion_minutos or 30), unit='minute')

                nuevo = Agendamiento(
                    cliente=cliente_obj,
                    servicio=servicio_obj,
                    empleado=empleado_obj,
                    inicia_en=inicia_en,
                    termina_en=termina_en,
                    estado=estado_clean,
                    notas=notas_val,
                )
                nuevo.full_clean()
                nuevo.save()
                creados += 1
            except Exception as exc:
                # CORRECCIÓN PYLANCE: Casteo explícito del índice para evitar problemas de tipos con Hashable
                fila_num = int(idx) + 1 if isinstance(idx, (int, float)) else str(idx)
                errores.append(f'Fila {fila_num}: {exc}')

        if errores:
            messages.warning(request, f'Creados {creados}. Errores en {len(errores)} filas.')
        else:
            messages.success(request, f'Cargados {creados} agendamientos correctamente.')
        return redirect('lista_agendamientos')

    return render(request, 'agendamientos/carga_masiva.html')