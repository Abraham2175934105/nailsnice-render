import io
import pandas as pd
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response
from core.utils import build_bulk_import_message
from clientes.models import Cliente
from usuarios.models import RolAcceso, Usuario, UsuarioRol
from .forms import ClienteForm

CLIENT_COLUMNS = [
    ('id_usuario', 'ID'),
    ('nombre', 'Nombre'),
    ('apellido', 'Apellido'),
    ('correo', 'Correo'),
    ('telefono', 'Telefono'),
    ('estado', 'Estado'),
    ('rol', 'Rol'),
    ('acepta_fidelizacion', 'Acepta fidelizacion'),
    ('acepta_fidelizacion', 'Fidelizacion'),
]
CLIENT_DEFAULT_COLUMNS = ['id_usuario', 'nombre', 'apellido', 'correo', 'telefono', 'estado', 'rol']
PAGE_MIN = 10
PAGE_MAX = 30


def _get_default_role_cliente():
    role_cliente, _ = RolAcceso.objects.get_or_create(
        nombre='Cliente',
        defaults={'descripcion': 'Cliente', 'codigo': 'CLIENTE'},
    )
    return role_cliente


def _resolve_role_from_value(role_value):
    """Auxiliar para resolver el rol en la carga masiva"""
    val = str(role_value or '').strip()
    if not val:
        return _get_default_role_cliente(), None
    
    # Intentar buscar por ID, código o nombre
    try:
        if val.isdigit():
            return RolAcceso.objects.get(pk=int(val)), None
        role = RolAcceso.objects.filter(Q(codigo__iexact=val) | Q(nombre__iexact=val)).first()
        if role:
            return role, None
        return None, f"El rol '{val}' no existe en el sistema."
    except Exception as e:
        return None, f"Error al resolver el rol: {str(e)}"


def _get_role_name(usuario):
    # Buscamos el rol a través de la tabla intermedia UsuarioRol
    user_role = UsuarioRol.objects.filter(usuario=usuario).select_related('rol').first()
    if user_role and user_role.rol:
        return user_role.rol.nombre
    return '-'


def _build_client_rows(queryset, selected):
    config = {
        'id_usuario': ('ID', lambda c: c.usuario_id),
        'nombre': ('Nombre', lambda c: c.usuario.nombre or ''),
        'apellido': ('Apellido', lambda c: c.usuario.apellido or ''),
        'correo': ('Correo', lambda c: c.usuario.correo),
        'telefono': ('Telefono', lambda c: c.usuario.telefono or ''),
        'estado': ('Estado', lambda c: c.usuario.estado),
        'rol': ('Rol', lambda c: _get_role_name(c.usuario)),
        'acepta_fidelizacion': ('Fidelizacion', lambda c: 'Sí' if c.acepta_fidelizacion else 'No'),
        'acepta_fidelizacion': ('Fidelizacion', lambda c: 'Si' if c.acepta_fidelizacion else 'No'),
    }
    keys = [k for k in selected if k in config] or CLIENT_DEFAULT_COLUMNS
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
    # CORRECCIÓN: Quitamos la relación inexistente del select_related
    clientes_qs = Cliente.objects.select_related('usuario').all()
    search = (request.GET.get('q') or '').strip()
    if search:
        clientes_qs = clientes_qs.filter(
            Q(usuario__nombre__icontains=search)
            | Q(usuario__apellido__icontains=search)
            | Q(usuario__correo__icontains=search)
            | Q(usuario__telefono__icontains=search)
        )

    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(clientes_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    for cliente in page_obj.object_list:
        cliente.rol_usuario = _get_role_name(cliente.usuario)

    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(CLIENT_COLUMNS)] or CLIENT_DEFAULT_COLUMNS
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

    return render(request, 'web/clientes.html', {
        'page_obj': page_obj,
        'clientes': page_obj.object_list,
        'search': search,
        'page_size': page_size,
        'columns_options': CLIENT_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
        'total_count': Cliente.objects.count(),
    })

@admin_required
def crear_clientes(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'web/formulario.html', {'form': form})

@admin_required
def editar_clientes(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    usuario = cliente.usuario
    if request.method == 'POST':
        form = ClienteForm(request.POST, usuario=usuario, perfil=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(usuario=usuario, perfil=cliente)
    return render(request, 'web/formulario.html', {'form': form})

@admin_required
def eliminar_clientes(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    usuario = cliente.usuario
    usuario.estado = 'INACTIVO'
    usuario.save(update_fields=['estado'])
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
        columns = set(df.columns)
        required_base = {'telefono', 'correo'}
        missing_base = required_base - columns
        if missing_base:
            missing_text = ", ".join(sorted(missing_base))
            messages.error(request, f'Faltan columnas requeridas: {missing_text}')
            return redirect('clientes_carga_masiva')

        has_names = {'nombre', 'apellido'}.issubset(columns) or {'nombre1', 'apellido1'}.issubset(columns)
        if not has_names:
            messages.error(request, 'El archivo debe incluir nombre y apellido (o nombre1 y apellido1).')
            return redirect('clientes_carga_masiva')

        creados = 0
        procesados = 0
        lista_duplicados = []
        lista_fallidos = []
        
        tiene_columna_rol = 'rol' in df.columns or 'id_rol' in df.columns or 'rol_nombre' in df.columns

        def _as_text(value):
            text = str(value or '').strip()
            return '' if text.lower() in {'nan', 'none', 'null'} else text

        def _normalize_email(value):
            return _as_text(value).lower()

        def _normalize_phone(value):
            return _as_text(value)

        email_candidates = {_normalize_email(v) for v in df['correo'].tolist() if _normalize_email(v)}
        phone_candidates = {_normalize_phone(v) for v in df['telefono'].tolist() if _normalize_phone(v)}

        existing_emails = set()
        existing_phones = set()

        if email_candidates:
            existing_emails.update(
                _normalize_email(v)
                for v in Usuario.objects.filter(correo__in=list(email_candidates)).values_list('correo', flat=True)
                if _normalize_email(v)
            )

        if phone_candidates:
            existing_phones.update(
                _normalize_phone(v)
                for v in Usuario.objects.filter(telefono__in=list(phone_candidates)).values_list('telefono', flat=True)
                if _normalize_phone(v)
            )

        seen_emails = set()
        seen_phones = set()

        for idx, row in df.iterrows():
            procesados += 1
            fila_num = int(idx) + 2 if isinstance(idx, (int, float)) else str(idx)
            
            nombre_legacy = _as_text(row.get('nombre', ''))
            apellido_legacy = _as_text(row.get('apellido', ''))
            nombre1_csv = _as_text(row.get('nombre1', ''))
            apellido1_csv = _as_text(row.get('apellido1', ''))

            nombre = nombre_legacy or nombre1_csv
            apellido = apellido_legacy or apellido1_csv

            if not nombre or not apellido:
                lista_fallidos.append(f'Fila {fila_num}: faltan datos de nombre/apellido.')
                continue

            data = {
                'nombre': nombre,
                'apellido': apellido,
                'telefono': _as_text(row.get('telefono', '')),
                'correo': _as_text(row.get('correo', '')),
            }

            correo_key = _normalize_email(data['correo'])
            telefono_key = _normalize_phone(data['telefono'])

            duplicate_reasons = []
            if correo_key:
                if correo_key in seen_emails:
                    duplicate_reasons.append(f"correo duplicado en archivo ({data['correo']})")
                elif correo_key in existing_emails:
                    duplicate_reasons.append(f"correo ya existe ({data['correo']})")

            if telefono_key:
                if telefono_key in seen_phones:
                    duplicate_reasons.append(f"teléfono duplicado en archivo ({data['telefono']})")
                elif telefono_key in existing_phones:
                    duplicate_reasons.append(f"teléfono ya existe ({data['telefono']})")

            if duplicate_reasons:
                lista_duplicados.append(f"Fila {fila_num}: {', '.join(duplicate_reasons)}")
                continue

            if correo_key:
                seen_emails.add(correo_key)
            if telefono_key:
                seen_phones.add(telefono_key)

            role_value = row.get('rol', row.get('id_rol', row.get('rol_nombre', ''))) if tiene_columna_rol else ''
            role_obj, role_error = _resolve_role_from_value(role_value)
            if role_error:
                lista_fallidos.append(f'Fila {fila_num}: {role_error}')
                continue

            acepta_fidelizacion = _as_bool(row.get('acepta_fidelizacion', True))
            acepta_fid = _as_text(row.get('acepta_fidelizacion', '1'))
            estado = _as_text(row.get('estado', 'ACTIVO')).upper() or 'ACTIVO'

            form = ClienteForm({
                'correo': data['correo'],
                'nombre': data['nombre'],
                'apellido': data['apellido'],
                'telefono': data['telefono'],
                'acepta_fidelizacion': acepta_fid not in {'0', 'false', 'no'},
                'estado': estado,
                'rol': role_obj.pk if role_obj else None,
                'password': _as_text(row.get('password', row.get('contrasena', row.get('contraseña', '')))),
                'es_staff': _as_text(row.get('es_staff', '0')) in {'1', 'true', 'si', 'yes'},
                'es_superusuario': _as_text(row.get('es_superusuario', '0')) in {'1', 'true', 'si', 'yes'},
            })

            if form.is_valid():
                form.save()
                creados += 1
            else:
                lista_fallidos.append(f"Fila {fila_num}: {form.errors.as_text().replace('*', '').strip()}")

        if not tiene_columna_rol:
            messages.info(request, 'No se envió columna rol. Se asignó Cliente por defecto donde aplicó.')

        duplicados_count = len(lista_duplicados)
        fallidos_count = len(lista_fallidos)

        msg_html = build_bulk_import_message(
            procesados=procesados,
            exitosos=creados,
            duplicados=duplicados_count,
            fallidos=fallidos_count,
            lista_duplicados=lista_duplicados,
            lista_fallidos=lista_fallidos
        )

        if fallidos_count > 0:
            messages.warning(request, msg_html, extra_tags='safe')
        else:
            messages.success(request, msg_html, extra_tags='safe')

        return redirect('lista_clientes')

    return render(request, 'web/carga_masiva_clientes.html')