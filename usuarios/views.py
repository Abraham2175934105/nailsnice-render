from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from rest_framework import viewsets
import io
import pandas as pd
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from core.auth import admin_required
from core.pdf_reports import build_crud_pdf_response


# Mixins y Permisos heredados del núcleo del proyecto
from core.audit import AuditViewSetMixin
from core.permissions import IsAdminOnly

# Modelos y Formularios del Módulo
from .models import Usuario, RolAcceso, Empleado
from .serializers import UsuarioSerializer, RolAccesoSerializer, EmpleadoSerializer
from .forms import UsuarioForm  # Formulario del módulo
from .forms import PasswordResetRequestForm, PasswordResetConfirmForm
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from .models import CodigoRecuperacion
from django.views.decorators.csrf import csrf_exempt


# =========================================================================
# 1. VISTAS PARA INTERFAZ GRÁFICA (UI SERVER-RENDERED - TEMPLATES .HTML)
# =========================================================================

ADMIN_COLUMNS = [
    ('nombre', 'Nombre'),
    ('apellido', 'Apellido'),
    ('correo', 'Correo'),
    ('telefono', 'Teléfono'),
    ('estado', 'Estado'),
    ('creado_en', 'Fecha Registro'),
]
ADMIN_DEFAULT_COLUMNS = ['nombre', 'apellido', 'correo', 'telefono', 'estado']

EMPLEADO_COLUMNS = [
    ('nombre', 'Nombre'),
    ('apellido', 'Apellido'),
    ('correo', 'Correo'),
    ('telefono', 'Teléfono'),
    ('estado', 'Estado'),
    ('codigo_empleado', 'Código Empleado'),
    ('cargo', 'Cargo'),
    ('fecha_contratacion', 'Fecha Contratación'),
    ('creado_en', 'Fecha Registro'),
]
EMPLEADO_DEFAULT_COLUMNS = ['nombre', 'apellido', 'correo', 'telefono', 'estado', 'cargo']

PAGE_MIN = 10
PAGE_MAX = 30

def _clamp_page_size(raw_value: str):
    try:
        value = int(raw_value)
    except Exception:
        value = PAGE_MIN
    return max(PAGE_MIN, min(PAGE_MAX, value))

def _build_admin_rows(queryset, selected):
    config = {
        'nombre': ('Nombre', lambda u: u.nombre),
        'apellido': ('Apellido', lambda u: u.apellido),
        'correo': ('Correo', lambda u: u.correo),
        'telefono': ('Teléfono', lambda u: u.telefono or 'No registrado'),
        'estado': ('Estado', lambda u: u.estado),
        'creado_en': ('Fecha Registro', lambda u: u.creado_en),
    }
    keys = [k for k in selected if k in config] or ADMIN_DEFAULT_COLUMNS
    rows = []
    for user in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(user)
        rows.append(row)
    return rows

def _export_admins(request, queryset, columns, fmt: str):
    rows = _build_admin_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"administradores.{fmt}"
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
            report_title='Reporte de Administradores',
            rows=rows,
            filename=filename,
        )
    return None

@admin_required
def admin_list(request):
    usuarios_qs = Usuario.objects.filter(
        roles_asignados__id_rol__nombre='Administrador'
    ).prefetch_related('roles_asignados__id_rol').order_by('nombre', 'apellido')
    
    search = (request.GET.get('q') or '').strip()
    if search:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre__icontains=search)
            | Q(apellido__icontains=search)
            | Q(correo__icontains=search)
            | Q(telefono__icontains=search)
        )
        
    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(usuarios_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(ADMIN_COLUMNS)] or ADMIN_DEFAULT_COLUMNS
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
            export_source = usuarios_qs
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_admins(request, export_source, selected_columns, export_fmt)
        if response:
            return response
            
    return render(request, 'admin/usuarios/admin_list.html', {
        'page_obj': page_obj,
        'usuarios_list': page_obj.object_list,
        'titulo_crud': "Equipo Administrativo",
        'badge_color': "#F8D7DA",
        'badge_text': "#721C24",
        'total_registros': paginator.count,
        'search': search,
        'page_size': page_size,
        'columns_options': ADMIN_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
    })

def _build_empleado_rows(queryset, selected):
    config = {
        'nombre': ('Nombre', lambda u: u.nombre),
        'apellido': ('Apellido', lambda u: u.apellido),
        'correo': ('Correo', lambda u: u.correo),
        'telefono': ('Teléfono', lambda u: u.telefono or 'No registrado'),
        'estado': ('Estado', lambda u: u.estado),
        'codigo_empleado': ('Código Empleado', lambda u: u.empleado.codigo_empleado if hasattr(u, 'empleado') and u.empleado else '—'),
        'cargo': ('Cargo', lambda u: u.empleado.cargo if hasattr(u, 'empleado') and u.empleado else '—'),
        'fecha_contratacion': ('Fecha Contratación', lambda u: u.empleado.fecha_contratacion.strftime('%d/%m/%Y') if hasattr(u, 'empleado') and u.empleado and u.empleado.fecha_contratacion else '—'),
        'creado_en': ('Fecha Registro', lambda u: u.creado_en),
    }
    keys = [k for k in selected if k in config] or EMPLEADO_DEFAULT_COLUMNS
    rows = []
    for user in queryset:
        row = {}
        for key in keys:
            label, fn = config[key]
            row[label] = fn(user)
        rows.append(row)
    return rows

def _export_empleados(request, queryset, columns, fmt: str):
    rows = _build_empleado_rows(queryset, columns)
    df = pd.DataFrame(rows)
    filename = f"empleados.{fmt}"
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
            report_title='Reporte de Empleados',
            rows=rows,
            filename=filename,
        )
    return None

@admin_required
def empleado_list(request):
    usuarios_qs = Usuario.objects.filter(
        roles_asignados__id_rol__nombre='Empleado'
    ).select_related('empleado').prefetch_related('roles_asignados__id_rol').order_by('nombre', 'apellido')
    
    search = (request.GET.get('q') or '').strip()
    if search:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre__icontains=search)
            | Q(apellido__icontains=search)
            | Q(correo__icontains=search)
            | Q(telefono__icontains=search)
        )
        
    page_size = _clamp_page_size(request.GET.get('page_size', PAGE_MIN))
    paginator = Paginator(usuarios_qs, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    selected_columns = [c for c in request.GET.getlist('columns') if c in dict(EMPLEADO_COLUMNS)] or EMPLEADO_DEFAULT_COLUMNS
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
            export_source = usuarios_qs
        elif export_scope == 'pages':
            export_source = []
            for page_num in export_pages:
                export_source.extend(list(paginator.get_page(page_num).object_list))
        else:
            export_source = paginator.get_page(export_page).object_list
        response = _export_empleados(request, export_source, selected_columns, export_fmt)
        if response:
            return response
            
    return render(request, 'admin/usuarios/empleado_list.html', {
        'page_obj': page_obj,
        'usuarios_list': page_obj.object_list,
        'titulo_crud': "Especialistas y Operativos",
        'badge_color': "#D1ECF1",
        'badge_text': "#0C5460",
        'total_registros': paginator.count,
        'search': search,
        'page_size': page_size,
        'columns_options': EMPLEADO_COLUMNS,
        'selected_columns': selected_columns,
        'export_scope': export_scope,
        'export_page': export_page,
        'export_pages': export_pages,
    })


class UsuarioCreateView(LoginRequiredMixin, CreateView):
    """
    Gestiona el formulario de creación de nuevos usuarios y asignación de rol.
    """
    model = Usuario
    form_class = UsuarioForm
    template_name = 'admin/usuarios/usuario_form.html'
    
    def get_success_url(self):
        rol_name = self.request.GET.get('rol')
        if rol_name == 'Administrador':
            return reverse_lazy('usuarios:admin_list')
        elif rol_name == 'Empleado':
            return reverse_lazy('usuarios:empleado_list')
        return reverse_lazy('usuarios:admin_list')
    
    def get_initial(self):
        initial = super().get_initial()
        rol_name = self.request.GET.get('rol')
        if rol_name:
            rol_obj = RolAcceso.objects.filter(nombre=rol_name).first()
            if rol_obj:
                initial['rol'] = rol_obj
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rol_fijo'] = self.request.GET.get('rol')
        return context

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
    success_url = reverse_lazy('usuarios:admin_list')  # Default fallback
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
        
    return redirect(request.META.get('HTTP_REFERER', 'usuarios:admin_list'))


# ------------------------------------------------------------------
# Password recovery endpoints (simple JSON API)
# ------------------------------------------------------------------


@csrf_exempt
@require_POST
def request_password_reset(request):
    """Recibe JSON `{'correo': 'user@example.com'}`. Genera código, guarda y envía email."""
    try:
        import json
        payload = json.loads(request.body)
        correo = payload.get('correo')
        if not correo:
            return JsonResponse({'error': 'correo is required'}, status=400)

        usuario = Usuario.objects.filter(correo__iexact=correo).first()

        # generar código de 6 dígitos
        codigo = str(random.randint(0, 999999)).zfill(6)
        ahora = timezone.now()
        expira = ahora + timedelta(minutes=10)

        CodigoRecuperacion.objects.create(
            usuario=usuario,
            correo=correo,
            codigo=codigo,
            expira_en=expira,
        )

        # render email
        context = {
            'codigo': codigo,
            'correo': correo,
            'expira_en': expira,
            'sitio_nombre': 'Profesional Beauty',
        }
        html = render_to_string('usuarios/email_recovery.html', context)
        subject = 'Tu codigo de verificacion - Nails Nice'
        from django.conf import settings as _s
        from_email = getattr(_s, 'DEFAULT_FROM_EMAIL', None)

        # send_mail maneja texto y html; fail_silently=False para ver errores reales
        send_mail(subject, f'Tu codigo de verificacion es: {codigo}', from_email, [correo], html_message=html, fail_silently=False)

        return JsonResponse({'status': 'ok', 'message': 'Código enviado si el correo existe'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def password_reset_request_page(request):
    """Interfaz HTML: formulario para solicitar código por correo."""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            usuario = Usuario.objects.filter(correo__iexact=correo).first()

            codigo = str(random.randint(0, 999999)).zfill(6)
            ahora = timezone.now()
            expira = ahora + timedelta(minutes=10)

            CodigoRecuperacion.objects.create(
                usuario=usuario,
                correo=correo,
                codigo=codigo,
                expira_en=expira,
            )

            context = {
                'codigo': codigo,
                'correo': correo,
                'expira_en': expira,
                'sitio_nombre': 'Profesional Beauty',
            }
            html = render_to_string('usuarios/email_recovery.html', context)
            subject = 'Tu codigo de verificacion - Nails Nice'
            from django.conf import settings as _s
            from_email = getattr(_s, 'DEFAULT_FROM_EMAIL', None)
            send_mail(subject, f'Tu codigo de verificacion es: {codigo}', from_email, [correo], html_message=html, fail_silently=False)

            messages.success(request, 'Si existe una cuenta con ese correo, se ha enviado un código de verificación.')
            return redirect(reverse('usuarios:password_reset_change_page') + f'?correo={correo}')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'usuarios/password_reset_request.html', {'form': form})


def password_reset_verify_page(request):
    """Interfaz HTML: formulario para verificar código y establecer nueva contraseña."""
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            codigo = form.cleaned_data['codigo']
            nueva = form.cleaned_data['nueva_password1']

            ahora = timezone.now()
            cr = CodigoRecuperacion.objects.filter(correo__iexact=correo, codigo=codigo, usado=False, expira_en__gte=ahora).order_by('-creado_en').first()
            if not cr:
                messages.error(request, 'Código inválido o expirado')
            elif not cr.usuario:
                messages.error(request, 'No existe usuario para este correo')
            else:
                usuario = cr.usuario
                usuario.set_password(nueva)
                usuario.save()

                cr.usado = True
                cr.save()

                messages.success(request, 'Contraseña actualizada. Ya puedes iniciar sesión.')
                return redirect('login')
    else:
        initial = {}
        correo_get = request.GET.get('correo')
        if correo_get:
            initial['correo'] = correo_get
        form = PasswordResetConfirmForm(initial=initial)

    return render(request, 'usuarios/password_reset_verify.html', {'form': form})


@csrf_exempt
@require_POST
def verify_password_reset(request):
    """Recibe JSON `{'correo','codigo','nueva_password'}`. Verifica y actualiza la contraseña."""
    try:
        import json
        payload = json.loads(request.body)
        correo = payload.get('correo')
        codigo = payload.get('codigo')
        nueva = payload.get('nueva_password')
        if not (correo and codigo and nueva):
            return JsonResponse({'error': 'correo, codigo y nueva_password son requeridos'}, status=400)

        ahora = timezone.now()
        cr = CodigoRecuperacion.objects.filter(correo__iexact=correo, codigo=codigo, usado=False, expira_en__gte=ahora).order_by('-creado_en').first()
        if not cr:
            return JsonResponse({'error': 'Código inválido o expirado'}, status=400)

        if not cr.usuario:
            # Ningún usuario registrado con ese correo
            return JsonResponse({'error': 'No existe usuario para este correo'}, status=400)

        usuario = cr.usuario
        usuario.set_password(nueva)
        usuario.save()

        cr.usado = True
        cr.save()

        return JsonResponse({'status': 'ok', 'message': 'Contraseña actualizada'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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