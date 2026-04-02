import io

import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from clientes.models import Cliente as ClienteRelacional
from usuarios.models import Rol, Usuario
from .models import Clientes
from .forms import ClientesForm

CLIENT_COLUMNS = [
    ('id', 'ID'),
    ('nombre', 'Nombre'),
    ('apellido', 'Apellido'),
    ('direccion', 'Dirección'),
    ('telefono', 'Teléfono'),
    ('correo', 'Correo'),
]
CLIENT_DEFAULT_COLUMNS = ['id', 'nombre', 'apellido', 'correo', 'telefono']
PAGE_MIN = 10
PAGE_MAX = 30


def _sync_relational_cliente(cliente_web: Clientes):
    role_cliente, _ = Rol.objects.get_or_create(nombre='Cliente', defaults={'descripcion': 'Cliente'})
    user, created = Usuario.objects.get_or_create(
        email=cliente_web.correo,
        defaults={
            'nombre1': cliente_web.nombre,
            'apellido1': cliente_web.apellido,
            'telefono': cliente_web.telefono,
            'estado_usuario': 'Activo',
            'id_rol': role_cliente,
        },
    )
    if created:
        user.set_unusable_password()

    user.nombre1 = cliente_web.nombre
    user.apellido1 = cliente_web.apellido
    user.telefono = cliente_web.telefono
    user.id_rol = role_cliente
    user.estado_usuario = 'Activo' if cliente_web.is_active else 'Inactivo'
    user.save()

    defaults = {'direccion': cliente_web.direccion}
    rel = ClienteRelacional.objects.filter(usuario=user).first()
    if rel:
        defaults['puntos_fidelidad'] = rel.puntos_fidelidad
    else:
        defaults['puntos_fidelidad'] = 0
    ClienteRelacional.objects.update_or_create(usuario=user, defaults=defaults)


def _build_client_rows(queryset, selected):
    config = {
        'id': ('ID', lambda c: c.id),
        'nombre': ('Nombre', lambda c: c.nombre),
        'apellido': ('Apellido', lambda c: c.apellido),
        'direccion': ('Dirección', lambda c: c.direccion),
        'telefono': ('Teléfono', lambda c: c.telefono),
        'correo': ('Correo', lambda c: c.correo),
    }
    keys = [k for k in selected if k in config] or ['id', 'nombre', 'apellido', 'correo', 'telefono']
    rows = []
    for c in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(c)
        rows.append(row)
    return rows


def _export_clientes(request, queryset, columns, fmt: str):
    rows = _build_client_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"clientes.{fmt}"
    if fmt == 'csv':
        buff = io.StringIO()
        df.to_csv(buff, index=False)
        return HttpResponse(buff.getvalue(), content_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'xlsx':
        buff = io.BytesIO()
        df.to_excel(buff, index=False)
        buff.seek(0)
        return HttpResponse(buff.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    if fmt == 'pdf':
        return build_crud_pdf_response(
            request=request,
            report_title='Reporte de Clientes',
            rows=rows,
            filename=filename,
        )
    return None

def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))


@admin_required
def lista_clientes(request):
    clientes_qs = Clientes.activos.all()
    search = (request.GET.get('q') or '').strip()
    if search:
        clientes_qs = clientes_qs.filter(
            Q(nombre__icontains=search) |
            Q(apellido__icontains=search) |
            Q(correo__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(clientes_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(CLIENT_COLUMNS)] or CLIENT_DEFAULT_COLUMNS
    export_scope = (request.GET.get('export_scope') or 'page').lower()
    export_page = request.GET.get('export_page') or page_obj.number

    export_fmt = (request.GET.get('export') or '').lower()
    if export_fmt in {'csv', 'xlsx', 'pdf'}:
        export_source = clientes_qs if export_scope == 'all' else paginator.get_page(export_page).object_list
        response = _export_clientes(request, export_source, selected_columns, export_fmt)
        if response:
            return response

    return render(request, 'web/clientes.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': CLIENT_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'legacy_count': Clientes.activos.count(),
        'rel_count': ClienteRelacional.objects.count(),
    })

@admin_required
def crear_clientes(request):
    if request.method == 'POST':
        form = ClientesForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            _sync_relational_cliente(cliente)
            return redirect('lista_clientes')
    else:
        form = ClientesForm()
    return render(request, 'web/formulario.html', {'form': form})

@admin_required
def editar_clientes(request, id):
    cliente = get_object_or_404(Clientes, id=id)
    if request.method == 'POST':
        form = ClientesForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            _sync_relational_cliente(cliente)
            return redirect('lista_clientes')
    else:
        form = ClientesForm(instance=cliente)
    return render(request, 'web/formulario.html', {'form': form})

@admin_required
def eliminar_clientes(request, id):
    cliente = get_object_or_404(Clientes, id=id)
    if cliente.is_active:
        cliente.is_active = False
        cliente.save(update_fields=['is_active'])
        user = Usuario.objects.filter(email=cliente.correo).first()
        if user:
            user.estado_usuario = 'Inactivo'
            user.save(update_fields=['estado_usuario'])
    return redirect('lista_clientes')


@admin_required
def carga_masiva_clientes(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Debes adjuntar un archivo CSV o Excel.')
            return redirect('clientes_carga_masiva')

        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception:
            messages.error(request, 'No se pudo leer el archivo. Usa CSV o Excel válido.')
            return redirect('clientes_carga_masiva')

        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {'nombre', 'apellido', 'direccion', 'telefono', 'correo'}
        missing = required - set(df.columns)
        if missing:
            messages.error(request, f'Faltan columnas requeridas: {", ".join(sorted(missing))}')
            return redirect('clientes_carga_masiva')

        creados = 0
        errores = []
        for idx, row in df.iterrows():
            data = {
                'nombre': str(row.get('nombre', '')).strip(),
                'apellido': str(row.get('apellido', '')).strip(),
                'direccion': str(row.get('direccion', '')).strip(),
                'telefono': str(row.get('telefono', '')).strip(),
                'correo': str(row.get('correo', '')).strip(),
            }
            form = ClientesForm(data)
            if form.is_valid():
                cliente = form.save()
                _sync_relational_cliente(cliente)
                creados += 1
            else:
                errores.append(f'Fila {idx + 1}: {form.errors.as_text()}')

        if errores:
            messages.warning(request, f'Creados {creados}. Errores en {len(errores)} filas.')
        else:
            messages.success(request, f'Cargados {creados} clientes correctamente.')
        return redirect('lista_clientes')

    return render(request, 'web/carga_masiva_clientes.html')