from django.shortcuts import render, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, Coalesce
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import re
import random
import string

# Importaciones para el Dashboard y Auth
from pedidos.models import Pedidos, Pedido, DetallePedido
from inventario.models import ProductoMaquillaje
from web.models import Clientes
from usuarios.models import Usuario, Rol
from core.security import (
    get_client_ip,
    is_locked,
    register_failure,
    clear_failures,
    security_event,
)

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

from core.auth import admin_required

@admin_required
def dashboard_view(request):
    # Métricas con datos reales
    pedidos_qs = Pedido.objects.all()
    legacy_pedidos_qs = Pedidos.activos.all() if hasattr(Pedidos, 'activos') else Pedidos.objects.all()

    ingresos = pedidos_qs.aggregate(total=Coalesce(Sum('total'), Decimal('0')))['total'] or Decimal('0')
    total_pedidos = pedidos_qs.count()
    if total_pedidos == 0:
        total_pedidos = legacy_pedidos_qs.count()
        ingresos = legacy_pedidos_qs.aggregate(total=Coalesce(Sum('precio'), Decimal('0')))['total'] or Decimal('0')
    total_clientes = Clientes.objects.count()
    total_productos = ProductoMaquillaje.activos.count()

    # Series mensuales (ventas y pedidos)
    monthly = (
        pedidos_qs
        .annotate(mes=TruncMonth('creado_en'))
        .values('mes')
        .annotate(
            monto=Coalesce(Sum('total'), Decimal('0')),
            pedidos=Count('id'),
        )
        .order_by('mes')
    )
    monthly_labels = [item['mes'].strftime('%b %Y') for item in monthly]
    monthly_sales = [float(item['monto']) for item in monthly]
    monthly_orders = [item['pedidos'] for item in monthly]

    # Fallback con tabla legacy en caso de no tener pedidos en el modelo nuevo.
    if not monthly_labels:
        legacy_monthly = (
            legacy_pedidos_qs
            .annotate(mes=TruncMonth('fecha'))
            .values('mes')
            .annotate(
                monto=Coalesce(Sum('precio'), Decimal('0')),
                pedidos=Count('id'),
            )
            .order_by('mes')
        )
        monthly_labels = [item['mes'].strftime('%b %Y') for item in legacy_monthly]
        monthly_sales = [float(item['monto']) for item in legacy_monthly]
        monthly_orders = [item['pedidos'] for item in legacy_monthly]

    # Top productos vendidos
    sales_expr = ExpressionWrapper(F('precio_unitario') * F('cantidad'), output_field=DecimalField(max_digits=12, decimal_places=2))
    top_vendidos = (
        DetallePedido.objects
        .values('producto__nombre')
        .annotate(unidades=Coalesce(Sum('cantidad'), 0), ventas=Coalesce(Sum(sales_expr), Decimal('0')))
        .order_by('-unidades')[:TOP_ITEMS_LIMIT]
    )
    top_names = [item['producto__nombre'] for item in top_vendidos]
    top_qty = [item['unidades'] for item in top_vendidos]
    top_sales = [float(item['ventas']) for item in top_vendidos]

    if not top_names:
        top_vendidos_legacy = (
            legacy_pedidos_qs
            .values('producto')
            .annotate(unidades=Coalesce(Sum('cantidad'), 0), ventas=Coalesce(Sum('precio'), Decimal('0')))
            .order_by('-unidades')[:TOP_ITEMS_LIMIT]
        )
        top_names = [item['producto'] for item in top_vendidos_legacy]
        top_qty = [item['unidades'] for item in top_vendidos_legacy]
        top_sales = [float(item['ventas']) for item in top_vendidos_legacy]

    # Productos con mayor stock
    stock_mas_altos = ProductoMaquillaje.activos.order_by('-stock')[:TOP_ITEMS_LIMIT]

    low_stock_qs = ProductoMaquillaje.activos.filter(stock__lte=LOW_STOCK_THRESHOLD).order_by('stock', 'nombre')
    low_stock_count = low_stock_qs.count()

    # Legacy últimos pedidos (para compatibilidad visual)
    ultimos_pedidos = Pedidos.objects.order_by('-id')[:5]
    productos_bajo_stock = low_stock_qs[:8]

    charts_payload = {
        'monthly_labels': monthly_labels,
        'monthly_sales': monthly_sales,
        'monthly_orders': monthly_orders,
        'top_names': top_names,
        'top_qty': top_qty,
        'top_sales': top_sales,
        'stock_names': [p.nombre for p in stock_mas_altos],
        'stock_qty': [p.stock for p in stock_mas_altos],
    }

    context = {
        'total_pedidos': total_pedidos,
        'ingresos': ingresos,
        'total_clientes': total_clientes,
        'total_productos': total_productos,
        'productos_bajo_stock': productos_bajo_stock,
        'low_stock_count': low_stock_count,
        'low_stock_threshold': LOW_STOCK_THRESHOLD,
        'ultimos_pedidos': ultimos_pedidos,
        'charts_payload': charts_payload,
    }
    return render(request, 'dashboard.html', context)

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
            usuario = Usuario.objects.filter(email=correo).first()
            user_auth = authenticate(request, email=correo, password=contrasena)
            active_ok = bool(
                usuario
                and getattr(usuario, 'is_active', True)
                and getattr(usuario, 'estado_usuario', 'Activo') == 'Activo'
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

                # Redirección según rol
                rol_id = getattr(user_auth, 'id_rol_id', None)
                if rol_id == 1 or getattr(user_auth, 'is_superuser', False):
                    return redirect('dashboard')
                elif rol_id == 2:
                    return redirect('index')
                else:
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
        nombre1 = (request.POST.get('nombre') or '').strip()
        nombre2 = (request.POST.get('nombre2') or '').strip()
        apellido1 = (request.POST.get('apellido') or '').strip()
        apellido2 = (request.POST.get('apellido2') or '').strip()
        direccion = (request.POST.get('direccion') or '').strip()
        telefono = (request.POST.get('telefono') or '').strip()
        correo = (request.POST.get('correo') or '').strip().lower()
        contrasena = request.POST.get('contrasena') or ''
        
        # Validaciones de Seguridad y Formato
        errores = False
        field_errors = {}

        # Solo letras A-Z sin espacios ni caracteres especiales (nombres y apellidos)
        name_pattern = r'^[A-Za-z]+'  # Solo letras, sin espacios ni caracteres especiales

        # Nombre y apellido obligatorios
        if not nombre1:
            field_errors['nombre'] = 'El primer nombre es obligatorio.'
            errores = True
        elif not re.fullmatch(name_pattern, nombre1):
            field_errors['nombre'] = 'El primer nombre solo puede contener letras, sin espacios ni caracteres especiales.'
            errores = True

        if not apellido1:
            field_errors['apellido'] = 'El primer apellido es obligatorio.'
            errores = True
        elif not re.fullmatch(name_pattern, apellido1):
            field_errors['apellido'] = 'El primer apellido solo puede contener letras, sin espacios ni caracteres especiales.'
            errores = True

        if nombre2:
            if not re.fullmatch(name_pattern, nombre2):
                field_errors['nombre2'] = 'El segundo nombre solo puede contener letras, sin espacios ni caracteres especiales.'
                errores = True

        if apellido2:
            if not re.fullmatch(name_pattern, apellido2):
                field_errors['apellido2'] = 'El segundo apellido solo puede contener letras, sin espacios ni caracteres especiales.'
                errores = True
            
        # Teléfono: solo números, 10-11 dígitos y sin duplicados
        if not re.fullmatch(r'\d{10,11}', telefono or ''):
            field_errors['telefono'] = 'El teléfono debe tener entre 10 y 11 dígitos numéricos.'
            errores = True
        else:
            if Usuario.objects.filter(telefono=telefono).exists():
                field_errors['telefono'] = 'El teléfono ya se encuentra registrado.'
                errores = True
        
        # Correo electrónico: formato, longitud y unicidad
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
                # Debe tener letras y números y no ser solo números
                if local_part.isdigit() or not (re.search(r'[A-Za-z]', local_part) and re.search(r'\d', local_part)):
                    field_errors['correo'] = 'El correo debe contener letras y números y no puede ser solo números.'
                    errores = True

            if Usuario.objects.filter(email=correo).exists():
                field_errors['correo'] = 'El correo ya está registrado.'
                errores = True

        # Dirección (validación simple de formato Colombia: Calle, Carrera, Avenida, etc.)
        if not direccion:
            field_errors['direccion'] = 'La dirección es obligatoria.'
            errores = True
        else:
            direccion_pattern = r'(?i)^(calle|cll|carrera|cra|cr|avenida|av|avda|transversal|tv|diagonal|dg)\s+\d+'
            if not re.match(direccion_pattern, direccion):
                field_errors['direccion'] = 'La dirección debe tener un formato de vía colombiano (ej: "Calle 123 #45-67").'
                errores = True

        # Contraseña: 8-20 caracteres, mayúscula, minúscula, número y carácter especial
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
                errores = True
            
        if errores:
            return render(request, 'registro.html', {'field_errors': field_errors})
            
        # Obtener o crear el Rol Cliente (id_rol_id = 2 en la base de datos)
        rol_cliente, _ = Rol.objects.get_or_create(nombre=Rol.CLIENTE)
        
        # Crear el Usuario de Django
        nuevo_usuario = Usuario.objects.create_user(
            email=correo,
            password=contrasena,
            nombre1=nombre1,
            nombre2=nombre2 or None,
            apellido1=apellido1,
            apellido2=apellido2 or None,
            telefono=telefono,
            id_rol=rol_cliente,
        )
        
        # Crear el registro local en web.Clientes
        Clientes.objects.create(
            nombre=nombre1,
            apellido=apellido1,
            direccion=direccion,
            telefono=telefono,
            correo=correo,
        )
        
        # No iniciar sesión automáticamente; redirigir al login
        messages.success(request, 'Usuario registrado correctamente. Ahora puedes iniciar sesión.')
        return redirect('login')
        
    return render(request, 'registro.html')


@login_required
def profile_view(request):
    user = request.user

    def _validate_user_fields(nombre1, nombre2, apellido1, apellido2, telefono):
        errors = {}
        name_pattern = r'^[A-Za-z]+'

        if not nombre1:
            errors['nombre'] = 'El primer nombre es obligatorio.'
        elif not re.fullmatch(name_pattern, nombre1):
            errors['nombre'] = 'Solo letras, sin espacios ni caracteres especiales.'

        if nombre2 and not re.fullmatch(name_pattern, nombre2):
            errors['nombre2'] = 'Solo letras, sin espacios ni caracteres especiales.'

        if not apellido1:
            errors['apellido'] = 'El primer apellido es obligatorio.'
        elif not re.fullmatch(name_pattern, apellido1):
            errors['apellido'] = 'Solo letras, sin espacios ni caracteres especiales.'

        if apellido2 and not re.fullmatch(name_pattern, apellido2):
            errors['apellido2'] = 'Solo letras, sin espacios ni caracteres especiales.'

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

    if hasattr(Pedidos, 'activos'):
        pedidos_usuario = Pedidos.activos.filter(usuario__iexact=user.email).order_by('-fecha', '-id')
    elif hasattr(Pedidos, 'objects'):
        pedidos_usuario = Pedidos.objects.filter(usuario__iexact=user.email).order_by('-id')
    else:
        pedidos_usuario = []
    cliente_db = Clientes.objects.filter(correo=user.email).first()
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
            nombre1 = (request.POST.get('nombre1') or '').strip()
            nombre2 = (request.POST.get('nombre2') or '').strip()
            apellido1 = (request.POST.get('apellido1') or '').strip()
            apellido2 = (request.POST.get('apellido2') or '').strip()
            telefono = (request.POST.get('telefono') or '').strip()
            direccion = (request.POST.get('direccion') or '').strip()
            password_actual = request.POST.get('password_actual') or ''

            errors = _validate_user_fields(nombre1, nombre2, apellido1, apellido2, telefono)

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
                    'cliente_direccion': getattr(cliente_db, 'direccion', ''),
                    'security_info': security_info,
                })

            user.nombre1 = nombre1
            user.nombre2 = nombre2 or None
            user.apellido1 = apellido1
            user.apellido2 = apellido2 or None
            user.telefono = telefono
            user.save()

            # Actualizamos también el cliente en la app web si existe
            cliente = Clientes.objects.filter(correo=user.email).first()
            if cliente:
                cliente.nombre = nombre1
                cliente.apellido = apellido1
                cliente.direccion = direccion
                cliente.telefono = telefono
                cliente.save()

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
                    'cliente_direccion': getattr(cliente_db, 'direccion', ''),
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
        'cliente_direccion': getattr(cliente_db, 'direccion', ''),
        'security_info': security_info,
    })


def _generate_reset_code(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))


def forgot_password_view(request):
    field_errors = {}

    if request.method == 'POST':
        metodo = request.POST.get('metodo')  # 'email' o 'sms'
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
                usuario = Usuario.objects.filter(email__iexact=valor).first()
            else:
                usuario = Usuario.objects.filter(telefono=valor).first()

            usuario_activo = bool(
                usuario
                and getattr(usuario, 'is_active', True)
                and getattr(usuario, 'estado_usuario', 'Activo') == 'Activo'
            )

            codigo = _generate_reset_code()
            request.session['reset_user_id'] = usuario.id if usuario_activo else -1
            request.session['reset_method'] = metodo
            request.session['reset_code'] = codigo
            request.session['reset_attempts'] = 0
            request.session['reset_decoy'] = not usuario_activo
            # Guardamos la fecha como string ISO para que sea serializable en sesiones JSON
            request.session['reset_created_at'] = timezone.now().isoformat()

            if usuario_activo and metodo == 'email':
                try:
                    send_mail(
                        subject='Código de verificación - NailsNice',
                        message=f'Tu código de verificación es: {codigo}',
                        from_email=None,  # usa DEFAULT_FROM_EMAIL si está definido en settings
                        recipient_list=[usuario.email],
                        fail_silently=False,  # en desarrollo conviene ver el error si falla el envío
                    )
                except Exception as e:
                    # En un entorno real se podría loggear; aquí mostramos un mensaje genérico
                    security_event('reset_email_delivery_error', request, extra={'identity': identity_key}, level='error')
                    messages.error(request, 'No se pudo procesar la solicitud en este momento. Intenta nuevamente.')
                    return render(request, 'forgot_password.html', {'field_errors': field_errors})
            elif usuario_activo:
                # Simulación de envío SMS: se imprime en consola del servidor
                print(f"[NailsNice] SMS a {usuario.telefono} - Código de verificación: {codigo}")

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

    # Validar expiración del código (ej: 10 minutos)
    created_at_str = request.session.get('reset_created_at')
    if created_at_str:
        created_at = parse_datetime(created_at_str)
        # Si por alguna razón no se puede parsear, tratamos el código como expirado
        if not created_at:
            _clear_reset_session(request)
            messages.error(request, 'El código de verificación ha expirado. Solicita uno nuevo.')
            return redirect('forgot_password')

        now = timezone.now()
        # Normalizamos ambas fechas a naive para evitar conflictos naive/aware,
        # independientemente de la configuración USE_TZ
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
            if request.session['reset_attempts'] >= 5:
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

    try:
        usuario = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
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
            # Reutilizamos las reglas del registro
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
            security_event('reset_password_success', request, extra={'email': usuario.email})

            # Limpiar estado de sesión del flujo de recuperación
            _clear_reset_session(request)

            messages.success(request, 'Contraseña actualizada con éxito. Ahora puedes iniciar sesión.')
            return redirect('login')

        return render(request, 'new_password.html', {'field_errors': field_errors, 'usuario': usuario})

    return render(request, 'new_password.html', {'usuario': usuario})
