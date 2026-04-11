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
    ('nombre1', 'Primer nombre'),
    ('nombre2', 'Segundo nombre'),
    ('apellido1', 'Primer apellido'),
    ('apellido2', 'Segundo apellido'),
    ('direccion', 'Dirección'),
    ('telefono', 'Teléfono'),
    ('correo', 'Correo'),
    ('rol', 'Rol'),
]
CLIENT_DEFAULT_COLUMNS = ['id', 'nombre', 'apellido', 'correo', 'telefono', 'rol', 'nombre1', 'apellido1']
PAGE_MIN = 10
PAGE_MAX = 30


def _get_default_role_cliente():
    role_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE, defaults={'descripcion': 'Cliente'})
    return role_cliente


def _is_admin_role(role):
    role_name = str(getattr(role, 'nombre', '') or '').strip().lower()
    return role_name in {'admin', 'administrador'}


def _resolve_role_from_value(raw_value):
    raw_text = str(raw_value or '').strip()
    if raw_text.lower() in {'nan', 'none', 'null', '-'}:
        raw_text = ''
    if not raw_text:
        return _get_default_role_cliente(), None

    role_id = None
    try:
        role_id = int(raw_text)
    except Exception:
        try:
            maybe_float = float(raw_text)
            if maybe_float.is_integer():
                role_id = int(maybe_float)
        except Exception:
            role_id = None

    if role_id is not None:
        role = Rol.objects.filter(pk=role_id).first()
        if role:
            return role, None

    role = Rol.objects.filter(nombre__iexact=raw_text).first()
    if role:
        return role, None

    aliases = {
        'admin': [Rol.ADMIN, 'Administrador', 'Admin'],
        'administrador': [Rol.ADMIN, 'Administrador', 'Admin'],
        'cliente': [Rol.CLIENTE, 'Cliente'],
        'empleado': [Rol.EMPLEADO, 'Empleado'],
    }

    for candidate in aliases.get(raw_text.lower(), []):
        role = Rol.objects.filter(nombre__iexact=candidate).first()
        if role:
            return role, None

    return None, f"Rol no válido '{raw_text}'. Usa Admin/Administrador, Cliente o Empleado."


def _build_user_lookup(clientes_iterable):
    emails = {
        str(getattr(c, 'correo', '') or '').strip().lower()
        for c in clientes_iterable
        if getattr(c, 'correo', None)
    }
    emails = {email for email in emails if email}
    if not emails:
        return {}

    users = Usuario.objects.filter(email__in=emails).select_related('id_rol')
    return {
        (u.email or '').strip().lower(): {
            'rol': u.id_rol.nombre if u.id_rol_id else '-',
            'nombre1': u.nombre1 or '',
            'nombre2': u.nombre2 or '',
            'apellido1': u.apellido1 or '',
            'apellido2': u.apellido2 or '',
        }
        for u in users
    }


def _sync_relational_cliente(cliente_web: Clientes, role=None, user_payload=None):
    role_cliente = role or _get_default_role_cliente()
    payload = user_payload or {}

    nombre1 = str(payload.get('nombre1') or '').strip() or cliente_web.nombre
    nombre2 = str(payload.get('nombre2') or '').strip() or None
    apellido1 = str(payload.get('apellido1') or '').strip() or cliente_web.apellido
    apellido2 = str(payload.get('apellido2') or '').strip() or None
    raw_password = str(payload.get('password') or '').strip()

    is_admin = _is_admin_role(role_cliente)

    user, created = Usuario.objects.get_or_create(
        email=cliente_web.correo,
        defaults={
            'nombre1': nombre1,
            'nombre2': nombre2,
            'apellido1': apellido1,
            'apellido2': apellido2,
            'telefono': cliente_web.telefono,
            'estado_usuario': 'Activo',
            'id_rol': role_cliente,
            'is_staff': is_admin,
            'is_superuser': is_admin,
            'is_active': True,
        },
    )

    if created and not raw_password:
        user.set_unusable_password()

    user.nombre1 = nombre1
    user.nombre2 = nombre2
    user.apellido1 = apellido1
    user.apellido2 = apellido2
    user.telefono = cliente_web.telefono
    user.id_rol = role_cliente
    user.estado_usuario = 'Activo' if cliente_web.is_active else 'Inactivo'
    user.is_active = bool(cliente_web.is_active)
    user.is_staff = is_admin
    user.is_superuser = is_admin

    if raw_password:
        user.set_password(raw_password)

    user.save()

    defaults = {'direccion': cliente_web.direccion}
    rel = ClienteRelacional.objects.filter(usuario=user).first()
    if rel:
        defaults['puntos_fidelidad'] = rel.puntos_fidelidad
    else:
        defaults['puntos_fidelidad'] = 0
    ClienteRelacional.objects.update_or_create(usuario=user, defaults=defaults)


def _build_client_rows(queryset, selected):
    user_lookup = _build_user_lookup(queryset)
    config = {
        'id': ('ID', lambda c: c.id),
        'nombre': ('Nombre', lambda c: c.nombre),
        'apellido': ('Apellido', lambda c: c.apellido),
        'nombre1': ('Primer nombre', lambda c: user_lookup.get(str(c.correo or '').strip().lower(), {}).get('nombre1', '-')),
        'nombre2': ('Segundo nombre', lambda c: user_lookup.get(str(c.correo or '').strip().lower(), {}).get('nombre2', '-')),
        'apellido1': ('Primer apellido', lambda c: user_lookup.get(str(c.correo or '').strip().lower(), {}).get('apellido1', '-')),
        'apellido2': ('Segundo apellido', lambda c: user_lookup.get(str(c.correo or '').strip().lower(), {}).get('apellido2', '-')),
        'direccion': ('Dirección', lambda c: c.direccion),
        'telefono': ('Teléfono', lambda c: c.telefono),
        'correo': ('Correo', lambda c: c.correo),
        'rol': ('Rol', lambda c: user_lookup.get(str(c.correo or '').strip().lower(), {}).get('rol', '-')),
    }
    keys = [k for k in selected if k in config] or ['id', 'nombre', 'apellido', 'correo', 'telefono', 'rol', 'nombre1', 'apellido1']
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
    users_by_email = _build_user_lookup(page_obj.object_list)
    for cliente in page_obj.object_list:
        email_key = str(cliente.correo or '').strip().lower()
        cliente.rol_usuario = users_by_email.get(email_key, {}).get('rol', '-')

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
        'legacy_count': Clientes.activos.count(),
        'rel_count': ClienteRelacional.objects.count(),
    })

@admin_required
def crear_clientes(request):
    if request.method == 'POST':
        form = ClientesForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            _sync_relational_cliente(cliente, role=form.cleaned_data.get('rol'), user_payload=form.cleaned_data)
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
            _sync_relational_cliente(cliente, role=form.cleaned_data.get('rol'), user_payload=form.cleaned_data)
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
    def _render_upload_page(feedback=None):
        return render(request, 'web/carga_masiva_clientes.html', {'upload_feedback': feedback})

    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            return _render_upload_page({
                'status': 'error',
                'summary': 'Debes adjuntar un archivo CSV o Excel.',
                'creados': 0,
                'duplicados': 0,
                'errores_total': 1,
                'errores': ['No se encontró un archivo para procesar.'],
                'warnings': [],
                'file_name': '',
                'errors_truncated': False,
            })

        try:
            if file.name.lower().endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception:
            return _render_upload_page({
                'status': 'error',
                'summary': 'No se pudo leer el archivo. Usa CSV o Excel válido.',
                'creados': 0,
                'duplicados': 0,
                'errores_total': 1,
                'errores': ['El formato no pudo procesarse correctamente.'],
                'warnings': [],
                'file_name': getattr(file, 'name', ''),
                'errors_truncated': False,
            })

        df.columns = [str(c).strip().lower() for c in df.columns]
        columns = set(df.columns)
        required_base = {'direccion', 'telefono', 'correo'}
        missing_base = required_base - columns
        if missing_base:
            missing_text = ", ".join(sorted(missing_base))
            return _render_upload_page({
                'status': 'error',
                'summary': f'Faltan columnas requeridas: {missing_text}',
                'creados': 0,
                'duplicados': 0,
                'errores_total': 1,
                'errores': [f'Incluye las columnas faltantes: {missing_text}.'],
                'warnings': [],
                'file_name': getattr(file, 'name', ''),
                'errors_truncated': False,
            })

        has_legacy_names = {'nombre', 'apellido'}.issubset(columns)
        has_relational_names = {'nombre1', 'apellido1'}.issubset(columns)
        if not (has_legacy_names or has_relational_names):
            return _render_upload_page({
                'status': 'error',
                'summary': 'El archivo debe incluir nombre y apellido, o nombre1 y apellido1.',
                'creados': 0,
                'duplicados': 0,
                'errores_total': 1,
                'errores': ['No se encontró un par válido de columnas para nombres.'],
                'warnings': [],
                'file_name': getattr(file, 'name', ''),
                'errors_truncated': False,
            })

        creados = 0
        duplicados = 0
        errores = []
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
                for v in Clientes.objects.filter(correo__in=list(email_candidates)).values_list('correo', flat=True)
                if _normalize_email(v)
            )
            existing_emails.update(
                _normalize_email(v)
                for v in Usuario.objects.filter(email__in=list(email_candidates)).values_list('email', flat=True)
                if _normalize_email(v)
            )

        if phone_candidates:
            existing_phones.update(
                _normalize_phone(v)
                for v in Clientes.objects.filter(telefono__in=list(phone_candidates)).values_list('telefono', flat=True)
                if _normalize_phone(v)
            )
            existing_phones.update(
                _normalize_phone(v)
                for v in Usuario.objects.filter(telefono__in=list(phone_candidates)).values_list('telefono', flat=True)
                if _normalize_phone(v)
            )

        seen_emails = set()
        seen_phones = set()

        for idx, row in df.iterrows():
            nombre_legacy = _as_text(row.get('nombre', ''))
            apellido_legacy = _as_text(row.get('apellido', ''))
            nombre1_csv = _as_text(row.get('nombre1', ''))
            apellido1_csv = _as_text(row.get('apellido1', ''))

            nombre = nombre_legacy or nombre1_csv
            apellido = apellido_legacy or apellido1_csv

            if not nombre or not apellido:
                errores.append(
                    f'Fila {idx + 1}: faltan datos de nombre/apellido. Usa nombre y apellido o nombre1 y apellido1.'
                )
                continue

            data = {
                'nombre': nombre,
                'apellido': apellido,
                'direccion': _as_text(row.get('direccion', '')),
                'telefono': _as_text(row.get('telefono', '')),
                'correo': _as_text(row.get('correo', '')),
            }

            correo_key = _normalize_email(data['correo'])
            telefono_key = _normalize_phone(data['telefono'])

            duplicate_reasons = []
            if correo_key:
                if correo_key in seen_emails:
                    duplicate_reasons.append(f"correo duplicado en el archivo ({data['correo']})")
                elif correo_key in existing_emails:
                    duplicate_reasons.append(f"correo ya existe ({data['correo']})")

            if telefono_key:
                if telefono_key in seen_phones:
                    duplicate_reasons.append(f"teléfono duplicado en el archivo ({data['telefono']})")
                elif telefono_key in existing_phones:
                    duplicate_reasons.append(f"teléfono ya existe ({data['telefono']})")

            if duplicate_reasons:
                duplicados += 1
                errores.append(f"Fila {idx + 1}: {'; '.join(duplicate_reasons)}.")
                continue

            if correo_key:
                seen_emails.add(correo_key)
            if telefono_key:
                seen_phones.add(telefono_key)

            role_value = row.get('rol', row.get('id_rol', row.get('rol_nombre', ''))) if tiene_columna_rol else ''
            role_obj, role_error = _resolve_role_from_value(role_value)
            if role_error:
                errores.append(f'Fila {idx + 1}: {role_error}')
                continue

            data.update({
                'nombre1': nombre1_csv or nombre,
                'nombre2': _as_text(row.get('nombre2', '')),
                'apellido1': apellido1_csv or apellido,
                'apellido2': _as_text(row.get('apellido2', '')),
                'password': _as_text(row.get('password', row.get('contrasena', row.get('contraseña', '')))),
                'rol': str(role_obj.pk),
            })

            form = ClientesForm(data)
            if form.is_valid():
                cliente = form.save()
                _sync_relational_cliente(cliente, role=role_obj, user_payload=form.cleaned_data)
                creados += 1
            else:
                errores.append(f'Fila {idx + 1}: {form.errors.as_text()}')

        warnings = []
        if not tiene_columna_rol:
            warnings.append('No se envió columna rol. Se asignó Cliente por defecto donde aplicó.')

        status = 'success'
        if errores and creados > 0:
            status = 'warning'
        elif errores:
            status = 'error'

        if errores:
            summary = f'Carga procesada: {creados} creado(s), {len(errores)} fila(s) con error.'
        else:
            summary = f'Carga completada: {creados} cliente(s) creado(s) sin errores.'

        max_errors = 80
        visible_errors = errores[:max_errors]

        return _render_upload_page({
            'status': status,
            'summary': summary,
            'creados': creados,
            'duplicados': duplicados,
            'errores_total': len(errores),
            'errores': visible_errors,
            'warnings': warnings,
            'file_name': getattr(file, 'name', ''),
            'errors_truncated': len(errores) > max_errors,
        })

    return _render_upload_page()