from django.shortcuts import render, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from decimal import Decimal
from datetime import timedelta, datetime, date

from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, IntegerField
from django.db.models.functions import TruncMonth, Coalesce
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
import re
import random
import string

# Importaciones para el Dashboard y Auth
from pedidos.models import PedidoVenta, DetallePedidoVenta
from productos.models import Producto
from inventario.models import SaldoInventario
from clientes.models import Cliente
from usuarios.models import Usuario, RolAcceso, UsuarioRol
from core.security import (
    get_client_ip,
    is_locked,
    register_failure,
    clear_failures,
    security_event,
)

# IMPORTACIÓN DE MODELOS BI UNMANAGED (OBJETIVO 7 - JUAN HERNÁNDEZ)
from core.models import (
    VWVentasDiarias,
    VWProductosTopMensual,
    VWSaludInventario,
    VWAgendamientosDiarios,
    VWValorCliente
)

from core.auth import admin_required

LOW_STOCK_THRESHOLD = 5
TOP_ITEMS_LIMIT = 5
AUTH_GENERIC_ERROR = 'Credenciales inválidas o cuenta no disponible.'
AUTH_RATE_LIMIT_ERROR = 'Demasiados intentos. Espera unos minutos e inténtalo de nuevo.'
RESET_GENERIC_SUCCESS = 'Si el usuario existe, enviaremos un código de verificación al medio seleccionado.'


def _clear_reset_session(request):
    for key in ['reset_user_id', 'reset_method', 'reset_code', 'reset_created_at', 'reset_verified', 'reset_attempts', 'reset_decoy']:
        if key in request.session:
            del request.session[key]


def index(request):
    cart = request.session.get('cart', {})
    return render(request, 'home.html', {'cart': cart})


@api_view(['GET'])
def home_api(request):
    return Response({
        "message": "Bienvenido a la API de NailsNice",
        "endpoints": {
            "usuarios": "/api/usuarios/",
            "productos": "/api/productos/",
            "pedidos": "/api/pedidos/",
            "clientes": "/api/clientes/",
            "servicios": "/api/servicios/",
            "admin": "/admin/"
        }
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    field_errors = {}
    session_notice = bool(request.GET.get('next'))

    if request.method == 'POST':
        correo = (request.POST.get('correo') or '').strip().lower()
        contrasena = request.POST.get('contrasena') or ''
        client_ip = get_client_ip(request)

        if is_locked('login_ip', client_ip) or (correo and is_locked('login_identity', correo)):
            field_errors['correo'] = AUTH_RATE_LIMIT_ERROR
            security_event('login_locked_attempt', request, extra={'email': correo}, level='warning')
            return render(request, 'login.html', {'field_errors': field_errors, 'session_notice': session_notice})

        if not correo:
            field_errors['correo'] = 'Debes ingresar tu correo electrónico.'
        if not contrasena:
            field_errors['contrasena'] = 'Debes ingresar tu contraseña.'

        if not field_errors:
            usuario = Usuario.objects.filter(correo=correo).first()
            user_auth = authenticate(request, username=correo, password=contrasena)
            active_ok = bool(
                usuario
                and (getattr(usuario, 'is_active', True) or str(getattr(usuario, 'estado', '')).upper() == 'ACTIVO')
            )

            if user_auth is None or not active_ok:
                register_failure('login_ip', client_ip, limit=8, window_seconds=600, lock_seconds=900)
                register_failure('login_identity', correo, limit=6, window_seconds=600, lock_seconds=900)
                field_errors['correo'] = AUTH_GENERIC_ERROR
                security_event('login_failed', request, extra={'email': correo}, level='warning')
            else:
                clear_failures('login_ip', client_ip)
                clear_failures('login_identity', correo)
                login(request, user_auth)
                request.session.cycle_key()
                security_event('login_success', request, extra={'email': correo})
                messages.success(request, 'Inicio de sesión exitoso.')

                user_role_obj = UsuarioRol.objects.filter(usuario=user_auth).select_related('id_rol').first()
                role_name = ""
                if user_role_obj and user_role_obj.rol:
                    role_name = str(user_role_obj.rol.nombre or '').strip().lower()

                if role_name == 'administrador' or getattr(user_auth, 'is_superuser', False):
                    return redirect('dashboard')
                if role_name == 'empleado':
                    return redirect('empleado_agendamientos')
                return redirect('index')

        if field_errors:
            return render(request, 'login.html', {'field_errors': field_errors, 'session_notice': session_notice})

    return render(request, 'login.html', {'session_notice': session_notice})


def logout_view(request):
    security_event('logout', request, extra={'email': getattr(request.user, 'email', None)})
    logout(request)
    request.session.flush()
    return redirect('index')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip()
        apellido = (request.POST.get('apellido') or '').strip()
        direccion = (request.POST.get('direccion') or '').strip()
        telefono = (request.POST.get('telefono') or '').strip()
        correo = (request.POST.get('correo') or '').strip().lower()
        contrasena = request.POST.get('contrasena') or ''
        
        errores = False
        field_errors = {}

        name_pattern = r'^[A-Za-z\s]+'

        if not nombre:
            field_errors['nombre'] = 'El nombre es obligatorio.'
            errores = True
        elif not re.fullmatch(name_pattern, nombre):
            field_errors['nombre'] = 'El nombre solo puede contener letras.'
            errores = True

        if not apellido:
            field_errors['apellido'] = 'El apellido es obligatorio.'
            errores = True
        elif not re.fullmatch(name_pattern, apellido):
            field_errors['apellido'] = 'El apellido solo puede contener letras.'
            errores = True
            
        if not re.fullmatch(r'\d{10,11}', telefono or ''):
            field_errors['telefono'] = 'El teléfono debe tener entre 10 y 11 dígitos numéricos.'
            errores = True
        else:
            if Usuario.objects.filter(telefono=telefono).exists():
                field_errors['telefono'] = 'El teléfono ya se encuentra registrado.'
                errores = True
        
        if not correo:
            field_errors['correo'] = 'El correo electrónico es obligatorio.'
            errores = True
        else:
            match = re.match(r'^([^@]+)@([^@]+\.[^@]+)$', correo)
            if not match:
                field_errors['correo'] = 'El formato del correo electrónico no es válido.'
                errores = True
            else:
                local_part = match.group(1)
                if len(local_part) < 6:
                    field_errors['correo'] = 'El correo debe tener al menos 6 caracteres antes del dominio.'
                    errores = True

            if Usuario.objects.filter(correo=correo).exists():
                field_errors['correo'] = 'El correo ya está registrado.'
                errores = True

        if not direccion:
            field_errors['direccion'] = 'La dirección es obligatoria.'
            errores = True

        if not contrasena:
            field_errors['contrasena'] = 'La contraseña es obligatoria.'
            errores = True
        else:
            if len(contrasena) < 8 or len(contrasena) > 20:
                field_errors['contrasena'] = 'La contraseña debe tener entre 8 y 20 caracteres.'
                errores = True
            if not re.search(r'[A-Z]', contrasena):
                field_errors['contrasena'] = 'La contraseña debe incluir al menos una letra mayúscula.'
                errores = True
            if not re.search(r'[a-z]', contrasena):
                field_errors['contrasena'] = 'La contraseña debe incluir al menos una letra minúscula.'
                errores = True
            if not re.search(r'\d', contrasena):
                field_errors['contrasena'] = 'La contraseña debe incluir al menos un número.'
                errores = True
            if not re.search(r'[^A-Za-z0-9]', contrasena):
                field_errors['contrasena'] = 'La contraseña debe incluir al menos un carácter especial.'
            
        if errores:
            return render(request, 'registro.html', {'field_errors': field_errors})
            
        rol_cliente, _ = RolAcceso.objects.get_or_create(
            codigo='CLIENTE',
            defaults={'nombre': 'Cliente', 'descripcion': 'Cliente', 'es_sistema': True},
        )
        
        nuevo_usuario = Usuario(
            correo=correo,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono
        )
        nuevo_usuario.set_password(contrasena)
        nuevo_usuario.save()

        UsuarioRol.objects.update_or_create(
            usuario=nuevo_usuario,
            defaults={'rol': rol_cliente},
        )
        
        messages.success(request, 'Usuario registrado correctamente. Ahora puedes iniciar sesión.')
        return redirect('login')
        
    return render(request, 'registro.html')


@login_required
def profile_view(request):
    user = request.user
    user_id = getattr(user, 'id_usuario', None) or getattr(user, 'id', None)

    def _validate_user_fields(nombre, apellido, telefono):
        errors = {}
        name_pattern = r'^[A-Za-z\s]+'

        if not nombre:
            errors['nombre'] = 'El nombre es obligatorio.'
        elif not re.fullmatch(name_pattern, nombre):
            errors['nombre'] = 'Solo letras y espacios permitidos.'

        if not apellido:
            errors['apellido'] = 'El apellido es obligatorio.'
        elif not re.fullmatch(name_pattern, apellido):
            errors['apellido'] = 'Solo letras y espacios permitidos.'

        if not re.fullmatch(r'\d{10,11}', telefono or ''):
            errors['telefono'] = 'El teléfono debe tener entre 10 y 11 dígitos numéricos.'

        return errors

    def _validate_password_rules(password):
        if len(password) < 8 or len(password) > 20:
            return 'La contraseña debe tener entre 8 y 20 caracteres.'
        if not re.search(r'[A-Z]', password):
            return 'Debe incluir al menos una letra mayúscula.'
        if not re.search(r'[a-z]', password):
            return 'Debe incluir al menos una letra minúscula.'
        if not re.search(r'\d', password):
            return 'Debe incluir al menos un número.'
        if not re.search(r'[^A-Za-z0-9]', password):
            return 'Debe incluir al menos un carácter especial.'
        return None

    pedidos_usuario = PedidoVenta.objects.filter(cliente__usuario_id=user_id).order_by('-id_pedido')
    cliente_db = Cliente.objects.filter(usuario_id=user_id).first()
    
    security_info = {
        'last_login': user.last_login,
        'current_ip': get_client_ip(request),
        'session_expire_browser_close': request.session.get_expire_at_browser_close(),
        'session_expires_at': timezone.now() + timedelta(seconds=request.session.get_expiry_age()),
    }

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        action = request.POST.get('action')
        if action == 'update_profile':
            nombre = (request.POST.get('nombre') or '').strip()
            apellido = (request.POST.get('apellido') or '').strip()
            telefono = (request.POST.get('telefono') or '').strip()
            direccion = (request.POST.get('direccion') or '').strip()
            password_actual = request.POST.get('password_actual') or ''

            errors = _validate_user_fields(nombre, apellido, telefono)

            direccion_pattern = r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+'
            if not direccion:
                errors['direccion'] = 'La dirección es obligatoria.'
            elif not re.match(direccion_pattern, direccion):
                errors['direccion'] = 'Usa un formato de vía colombiano (ej: "Calle 123 #45-67").'

            if not password_actual or not user.check_password(password_actual):
                errors['password_actual'] = 'Debes confirmar con tu contraseña actual.'

            if errors:
                if is_ajax:
                    first_error = next(iter(errors.values())) if errors else 'Error al validar datos.'
                    return JsonResponse({'ok': False, 'error': first_error, 'errors': errors}, status=400)
                return render(request, 'perfil.html', {
                    'field_errors': errors,
                    'pedidos': pedidos_usuario,
                    'cliente_direccion': getattr(cliente_db, 'direccion', '') if hasattr(cliente_db, 'direccion') else '',
                    'security_info': security_info,
                })

            setattr(user, 'nombre', nombre)
            setattr(user, 'apellido', apellido)
            setattr(user, 'telefono', telefono)
            user.save()

            if cliente_db is not None:
                if hasattr(cliente_db, 'direccion'):
                    setattr(cliente_db, 'direccion', direccion)
                    cliente_db.save()

            if is_ajax:
                return JsonResponse({'ok': True, 'message': 'Datos actualizados correctamente.', 'redirect': reverse('perfil')})
            messages.success(request, 'Datos actualizados correctamente.')
            return redirect('perfil')

        if action == 'change_password':
            actual = request.POST.get('actual') or ''
            nueva = request.POST.get('nueva') or ''
            confirmar = request.POST.get('confirmar') or ''

            errors = {}
            if not user.check_password(actual):
                errors['actual'] = 'La contraseña actual no es correcta.'
            if not nueva or not confirmar:
                errors['nueva'] = 'Debes ingresar y confirmar la nueva contraseña.'
            elif nueva != confirmar:
                errors['nueva'] = 'Las contraseñas no coinciden.'
            else:
                rule_error = _validate_password_rules(nueva)
                if rule_error:
                    errors['nueva'] = rule_error

            if errors:
                if is_ajax:
                    first_error = next(iter(errors.values())) if errors else 'Error al validar datos.'
                    return JsonResponse({'ok': False, 'error': first_error, 'errors': errors}, status=400)
                return render(request, 'perfil.html', {
                    'field_errors': errors,
                    'pedidos': pedidos_usuario,
                    'cliente_direccion': getattr(cliente_db, 'direccion', '') if hasattr(cliente_db, 'direccion') else '',
                    'security_info': security_info,
                })

            user.set_password(nueva)
            user.save()
            update_session_auth_hash(request, user)
            if is_ajax:
                return JsonResponse({'ok': True, 'message': 'Contraseña actualizada con éxito.', 'redirect': reverse('perfil')})
            messages.success(request, 'Contraseña actualizada con éxito.')
            return redirect('perfil')

    return render(request, 'perfil.html', {
        'pedidos': pedidos_usuario,
        'cliente_direccion': getattr(cliente_db, 'direccion', '') if hasattr(cliente_db, 'direccion') else '',
        'security_info': security_info,
    })


def _generate_reset_code(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))


def forgot_password_view(request):
    field_errors = {}

    if request.method == 'POST':
        metodo = request.POST.get('metodo')
        valor = (request.POST.get('identificador') or '').strip()
        client_ip = get_client_ip(request)
        identity_key = valor.lower() if metodo == 'email' else valor

        if is_locked('reset_ip', client_ip) or (identity_key and is_locked('reset_identity', identity_key)):
            field_errors['identificador'] = AUTH_RATE_LIMIT_ERROR
            security_event('reset_locked_attempt', request, extra={'identity': identity_key}, level='warning')
            return render(request, 'forgot_password.html', {'field_errors': field_errors})

        if metodo not in ['email', 'sms']:
            field_errors['metodo'] = 'Debes seleccionar un método de recuperación.'
        elif not valor:
            field_errors['identificador'] = 'Ingresa tu correo o teléfono.'

        if not field_errors:
            usuario = None
            if metodo == 'email':
                usuario = Usuario.objects.filter(correo__iexact=valor).first()
            else:
                usuario = Usuario.objects.filter(telefono=valor).first()

            usuario_activo = bool(
                usuario is not None
                and getattr(usuario, 'is_active', True)
                and str(getattr(usuario, 'estado', 'Activo')).upper() == 'ACTIVO'
            )

            codigo = _generate_reset_code()
            
            if usuario is not None and usuario_activo:
                u_id = getattr(usuario, 'id_usuario', None) or getattr(usuario, 'id', -1)
                u_telefono = getattr(usuario, 'telefono', '')
                u_correo = getattr(usuario, 'correo', '')
            else:
                u_id = -1
                u_telefono = ''
                u_correo = ''

            request.session['reset_user_id'] = u_id
            request.session['reset_method'] = metodo
            request.session['reset_code'] = codigo
            request.session['reset_attempts'] = 0
            request.session['reset_decoy'] = not usuario_activo
            request.session['reset_created_at'] = timezone.now().isoformat()

            if usuario_activo and metodo == 'email' and u_correo:
                try:
                    send_mail(
                        subject='Código de verificación - NailsNice',
                        message=f'Tu código de verificación es: {codigo}',
                        from_email=None,
                        recipient_list=[u_correo],
                        fail_silently=False,
                    )
                except Exception:
                    security_event('reset_email_delivery_error', request, extra={'identity': identity_key}, level='error')
                    messages.error(request, 'No se pudo procesar la solicitud en este momento. Intenta nuevamente.')
                    return render(request, 'forgot_password.html', {'field_errors': field_errors})
            elif usuario_activo:
                print(f"[NailsNice] SMS a {u_telefono} - Código de verificación: {codigo}")

            if usuario_activo:
                clear_failures('reset_ip', client_ip)
                clear_failures('reset_identity', identity_key)
                security_event('reset_code_issued', request, extra={'identity': identity_key})
            else:
                register_failure('reset_ip', client_ip, limit=12, window_seconds=900, lock_seconds=1200)
                register_failure('reset_identity', identity_key, limit=8, window_seconds=900, lock_seconds=1200)
                security_event('reset_requested_unknown_identity', request, extra={'identity': identity_key}, level='warning')

            messages.success(request, RESET_GENERIC_SUCCESS)
            return redirect('verify_reset_code')

        return render(request, 'forgot_password.html', {'field_errors': field_errors})

    return render(request, 'forgot_password.html')


def verify_reset_code_view(request):
    client_ip = get_client_ip(request)

    if is_locked('reset_verify_ip', client_ip):
        messages.error(request, AUTH_RATE_LIMIT_ERROR)
        return redirect('forgot_password')

    if 'reset_user_id' not in request.session or not request.session.get('reset_code'):
        messages.error(request, 'El código es inválido o expiró. Solicita uno nuevo.')
        return redirect('forgot_password')

    created_at_str = request.session.get('reset_created_at')
    if created_at_str:
        created_at = parse_datetime(str(created_at_str))
        if not created_at:
            _clear_reset_session(request)
            messages.error(request, 'El código de verificación ha expirado. Solicita uno nuevo.')
            return redirect('forgot_password')

        now = timezone.now()
        if timezone.is_aware(created_at):
            created_at = timezone.make_naive(created_at, timezone.get_current_timezone())
        if timezone.is_aware(now):
            now = timezone.make_naive(now, timezone.get_current_timezone())

        if (now - created_at).total_seconds() > 10 * 60:
            _clear_reset_session(request)
            messages.error(request, 'El código ha expirado. Solicita uno nuevo.')
            return redirect('forgot_password')
    else:
        _clear_reset_session(request)
        messages.error(request, 'El código de verificación ha expirado. Solicita uno nuevo.')
        return redirect('forgot_password')

    field_errors = {}

    if request.method == 'POST':
        codigo = (request.POST.get('codigo') or '').strip()
        if not codigo:
            field_errors['codigo'] = 'Ingresa el código de verificación.'
        elif codigo != request.session.get('reset_code'):
            request.session['reset_attempts'] = int(request.session.get('reset_attempts', 0) or 0) + 1
            register_failure('reset_verify_ip', client_ip, limit=10, window_seconds=600, lock_seconds=900)
            security_event(
                'reset_code_invalid',
                request,
                extra={'attempts': request.session['reset_attempts']},
                level='warning',
            )
            if int(request.session['reset_attempts']) >= 5:
                _clear_reset_session(request)
                messages.error(request, 'El código es inválido o expiró. Solicita uno nuevo.')
                return redirect('forgot_password')
            field_errors['codigo'] = 'El código es inválido o expiró.'
        else:
            request.session['reset_verified'] = True
            request.session['reset_attempts'] = 0
            clear_failures('reset_verify_ip', client_ip)
            security_event('reset_code_validated', request)
            return redirect('new_password')

        return render(request, 'verify_reset_code.html', {'field_errors': field_errors})

    return render(request, 'verify_reset_code.html')


def new_password_view(request):
    user_id = request.session.get('reset_user_id')
    verified = request.session.get('reset_verified')

    if user_id is None or not verified:
        messages.error(request, 'El enlace para restablecer la contraseña no es válido o ha expirado.')
        return redirect('forgot_password')

    usuario = Usuario.objects.filter(id_usuario=user_id).first() or Usuario.objects.filter(id=user_id).first()
    if usuario is None:
        _clear_reset_session(request)
        messages.error(request, 'El enlace para restablecer la contraseña no es válido o ha expirado.')
        security_event('reset_password_invalid_session', request, level='warning')
        return redirect('forgot_password')

    field_errors = {}

    if request.method == 'POST':
        nueva = request.POST.get('nueva') or ''
        confirmar = request.POST.get('confirmar') or ''

        if not nueva or not confirmar:
            field_errors['nueva'] = 'Debes ingresar y confirmar la nueva contraseña.'
        elif nueva != confirmar:
            field_errors['nueva'] = 'Las contraseñas no coinciden.'
        else:
            if len(nueva) < 8 or len(nueva) > 20:
                field_errors['nueva'] = 'La contraseña debe tener entre 8 y 20 caracteres.'
            if not field_errors and not re.search(r'[A-Z]', nueva):
                field_errors['nueva'] = 'La contraseña debe incluir al menos una letra mayúscula.'
            if not field_errors and not re.search(r'[a-z]', nueva):
                field_errors['nueva'] = 'La contraseña debe incluir al menos una letra minúscula.'
            if not field_errors and not re.search(r'\d', nueva):
                field_errors['nueva'] = 'La contraseña debe incluir al menos un número.'
            if not field_errors and not re.search(r'[^A-Za-z0-9]', nueva):
                field_errors['nueva'] = 'La contraseña debe incluir al menos un carácter especial.'

        if not field_errors:
            usuario.set_password(nueva)
            usuario.save()
            security_event('reset_password_success', request, extra={'email': getattr(usuario, 'correo', '')})

            _clear_reset_session(request)

            messages.success(request, 'Contraseña actualizada con éxito. Ahora puedes iniciar sesión.')
            return redirect('login')

        return render(request, 'new_password.html', {'field_errors': field_errors, 'usuario': usuario})

    return render(request, 'new_password.html', {'usuario': usuario})


@admin_required
def dashboard_view(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    hoy: date = datetime.now().date()
    start_date: date = hoy - timedelta(days=30)
    end_date: date = hoy

    if start_date_str and end_date_str:
        parsed_start = parse_date(start_date_str)
        parsed_end = parse_date(end_date_str)
        if parsed_start is not None and parsed_end is not None:
            start_date = parsed_start
            end_date = parsed_end

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    total_pedidos = PedidoVenta.objects.filter(
        realizado_en__range=(start_datetime, end_datetime)
    ).count()

    ingresos_data = PedidoVenta.objects.filter(
        realizado_en__range=(start_datetime, end_datetime)
    ).aggregate(total=Sum('monto_total'))
    ingresos = ingresos_data['total'] if ingresos_data['total'] else 0.0

    total_clientes = PedidoVenta.objects.filter(
        realizado_en__range=(start_datetime, end_datetime)
    ).values('cliente').distinct().count()

    total_productos = Producto.objects.filter(activo=True).count()

    ventas_mensuales = PedidoVenta.objects.filter(
        realizado_en__range=(start_datetime, end_datetime)
    ).annotate(
        mes=TruncMonth('realizado_en')
    ).values('mes').annotate(
        total_ventas=Sum('monto_total'),
        total_pedidos=Count('id_pedido')
    ).order_by('mes')

    monthly_labels = [v['mes'].strftime('%b %Y') for v in ventas_mensuales if v['mes'] is not None]
    monthly_sales = [float(v['total_ventas']) for v in ventas_mensuales if v['total_ventas'] is not None]
    monthly_orders = [v['total_pedidos'] for v in ventas_mensuales]

    top_productos = DetallePedidoVenta.objects.filter(
        pedido__realizado_en__range=(start_datetime, end_datetime)
    ).values(
        nombre=F('producto__nombre')
    ).annotate(
        unidades=Sum('cantidad'),
        total_recaudado=Sum(F('cantidad') * F('precio_unitario'))
    ).order_by('-unidades')[:5]

    top_names = [p['nombre'] for p in top_productos]
    top_qty = [p['unidades'] for p in top_productos]
    top_sales = [float(p['total_recaudado']) for p in top_productos]

    low_stock_threshold = 5
    
    stock_expr = ExpressionWrapper(F('cantidad_existencia') - F('cantidad_reservada'), output_field=IntegerField())
    
    # RESOLUCIÓN SEGURA DE ATRIBUTOS PARA SALDOINVENTARIO (EVITA ALERTAS DE PYLANCE Y ERRORES 500)
    productos_stock_list = SaldoInventario.objects.annotate(
        stock=stock_expr
    ).values(
        'stock', 
        nombre=F('variante__producto__nombre')
    ).order_by('-stock')[:5]
    
    stock_names = [str(item.get('nombre', '')) for item in productos_stock_list]
    stock_qty = [item.get('stock', 0) for item in productos_stock_list]

    productos_bajo_stock = SaldoInventario.objects.annotate(
        stock=stock_expr
    ).filter(
        stock__lte=low_stock_threshold
    ).values(
        'stock', 
        nombre=F('variante__producto__nombre')
    )
    low_stock_count = productos_bajo_stock.count()

    ultimos_pedidos = PedidoVenta.objects.filter(
        realizado_en__range=(start_datetime, end_datetime)
    ).select_related('cliente__usuario').order_by('-realizado_en')[:5]

    charts_payload = {
        'monthly_labels': monthly_labels,
        'monthly_sales': monthly_sales,
        'monthly_orders': monthly_orders,
        'top_names': top_names,
        'top_qty': top_qty,
        'top_sales': top_sales,
        'stock_names': stock_names,
        'stock_qty': stock_qty
    }

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_pedidos': total_pedidos,
        'ingresos': ingresos,
        'total_clientes': total_clientes,
        'total_productos': total_productos,
        'low_stock_count': low_stock_count,
        'low_stock_threshold': low_stock_threshold,
        'productos_bajo_stock': productos_bajo_stock,
        'ultimos_pedidos': ultimos_pedidos,
        'charts_payload': charts_payload
    }

    return render(request, 'dashboard.html', context)