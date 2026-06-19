from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from rest_framework import viewsets

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

class AdministradorListView(LoginRequiredMixin, ListView):
    model = Usuario
    template_name = 'admin/usuarios/admin_list.html'
    context_object_name = 'usuarios_list'
    
    def get_queryset(self):
        return Usuario.objects.filter(
            roles_asignados__id_rol__nombre='Administrador'
        ).prefetch_related('roles_asignados__id_rol').order_by('nombre', 'apellido')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_crud'] = "Equipo Administrativo"
        context['badge_color'] = "#F8D7DA"
        context['badge_text'] = "#721C24"
        return context

class EmpleadoUIListView(LoginRequiredMixin, ListView):
    model = Usuario
    template_name = 'admin/usuarios/empleado_list.html'
    context_object_name = 'usuarios_list'
    
    def get_queryset(self):
        return Usuario.objects.filter(
            roles_asignados__id_rol__nombre='Empleado'
        ).prefetch_related('roles_asignados__id_rol').order_by('nombre', 'apellido')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_crud'] = "Especialistas y Operativos"
        context['badge_color'] = "#D1ECF1"
        context['badge_text'] = "#0C5460"
        return context


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
        subject = 'Código de recuperación de contraseña - Profesional Beauty'
        from_email = None  # Django usará DEFAULT_FROM_EMAIL

        # send_mail maneja texto y html
        send_mail(subject, f'Código: {codigo}', from_email, [correo], html_message=html)

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
            subject = 'Código de recuperación de contraseña - Profesional Beauty'
            send_mail(subject, f'Código: {codigo}', None, [correo], html_message=html)

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