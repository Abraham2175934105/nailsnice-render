from django.shortcuts import render, redirect
# pyrefly: ignore [missing-import]
from rest_framework.decorators import api_view
# pyrefly: ignore [missing-import]
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
        from core.forms import RegistroForm
        from clientes.models import Cliente, DireccionUsuario

        form = RegistroForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            telefono = form.cleaned_data['telefono']
            linea1 = form.cleaned_data['linea1']
            ciudad = form.cleaned_data['ciudad']
            departamento = form.cleaned_data['departamento']
            contrasena = form.cleaned_data['contrasena']
            
            rol_cliente, _ = RolAcceso.objects.get_or_create(
                codigo='CLIENTE',
                defaults={'nombre': 'Cliente', 'descripcion': 'Cliente', 'es_sistema': True},
            )
            
            from django.db import transaction
            try:
                with transaction.atomic():
                    nuevo_usuario = Usuario(
                        correo=correo,
                        nombre=nombre,
                        apellido=apellido,
                        telefono=telefono,
                        estado='ACTIVO'
                    )
                    nuevo_usuario.set_password(contrasena)
                    nuevo_usuario.save()

                    # Create the Client profile
                    Cliente.objects.create(
                        usuario=nuevo_usuario,
                        acepta_fidelizacion=True
                    )

                    # Create default shipping address for the user
                    DireccionUsuario.objects.create(
                        usuario=nuevo_usuario,
                        tipo_direccion='ENVIO',
                        etiqueta='Principal',
                        nombre_destinatario=f"{nombre} {apellido}",
                        linea1=linea1,
                        ciudad=ciudad,
                        departamento=departamento,
                        codigo_pais='CO',
                        es_predeterminada_envio=True,
                        es_predeterminada_factura=True
                    )

                    UsuarioRol.objects.update_or_create(
                        usuario=nuevo_usuario,
                        defaults={'rol': rol_cliente},
                    )
                
                messages.success(request, 'Usuario registrado correctamente. Ahora puedes iniciar sesión.')
                return redirect('login')
            except Exception as e:
                form.add_error(None, f"Error al registrar el usuario: {str(e)}")
                field_errors = {field: error_list[0] for field, error_list in form.errors.items()}
                # Add non-field errors to the response if they exist
                if form.non_field_errors():
                    field_errors['non_field_errors'] = form.non_field_errors()[0]
                return render(request, 'registro.html', {'field_errors': field_errors})
        else:
            field_errors = {field: error_list[0] for field, error_list in form.errors.items()}
            return render(request, 'registro.html', {'field_errors': field_errors})
            
    return render(request, 'registro.html')


@login_required
def profile_view(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from core.forms import PerfilUpdateForm
    from clientes.models import DireccionUsuario

    user = request.user
    user_id = getattr(user, 'id_usuario', None) or getattr(user, 'id', None)

    direccion = DireccionUsuario.objects.filter(usuario=user, es_predeterminada_envio=True).first()

    pedidos_qs = (
        PedidoVenta.objects
        .filter(cliente__usuario=user)
        .select_related('direccion_envio')
        .prefetch_related('detalles__variante__producto')
        .order_by('-id_pedido')
    )

    pedidos_usuario = []
    for p in pedidos_qs:
        detalles = list(p.detalles.all())
        producto_names = [d.nombre_producto_snapshot or d.variante.producto.nombre for d in detalles if d.variante]
        producto_str = ", ".join(producto_names) if producto_names else "Sin productos"
        total_cantidad = sum(d.cantidad for d in detalles)

        direccion_str = ""
        if p.direccion_envio:
            dir_parts = [p.direccion_envio.linea1]
            if p.direccion_envio.ciudad:
                dir_parts.append(p.direccion_envio.ciudad)
            if p.direccion_envio.departamento:
                dir_parts.append(p.direccion_envio.departamento)
            direccion_str = ", ".join(dir_parts)

        pedidos_usuario.append({
            'id': p.id_pedido,
            'fecha': p.realizado_en.strftime('%d/%m/%Y %H:%M') if p.realizado_en else '',
            'estado': p.get_estado_display() if hasattr(p, 'get_estado_display') else p.estado,
            'precio': p.monto_total,
            'producto': producto_str,
            'cantidad': total_cantidad,
            'direccion': direccion_str,
        })

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
            form = PerfilUpdateForm(request.POST, instance=user)
            password_actual = request.POST.get('password_actual') or ''

            errors = {}
            if not form.is_valid():
                errors = {field: error_list[0] for field, error_list in form.errors.items()}

            if not password_actual or not user.check_password(password_actual):
                errors['password_actual'] = 'Debes confirmar con tu contraseña actual.'

            if errors:
                if is_ajax:
                    first_error = next(iter(errors.values())) if errors else 'Error al validar datos.'
                    return JsonResponse({'ok': False, 'error': first_error, 'errors': errors}, status=400)
                return render(request, 'perfil.html', {
                    'field_errors': errors,
                    'pedidos': pedidos_usuario,
                    'security_info': security_info,
                    'direccion': direccion,
                })

            form.save()

            # Sincronizar dirección
            linea1_val = form.cleaned_data['linea1']
            ciudad_val = form.cleaned_data['ciudad']
            departamento_val = form.cleaned_data['departamento']

            if direccion:
                direccion.linea1 = linea1_val
                direccion.ciudad = ciudad_val
                direccion.departamento = departamento_val
                direccion.nombre_destinatario = f"{user.nombre} {user.apellido}"
                direccion.save()
            else:
                direccion = DireccionUsuario.objects.create(
                    usuario=user,
                    tipo_direccion='ENVIO',
                    etiqueta='Principal',
                    nombre_destinatario=f"{user.nombre} {user.apellido}",
                    linea1=linea1_val,
                    ciudad=ciudad_val,
                    departamento=departamento_val,
                    codigo_pais='CO',
                    es_predeterminada_envio=True,
                    es_predeterminada_factura=True
                )

            if is_ajax:
                return JsonResponse({'ok': True, 'message': 'Datos actualizados correctamente.', 'redirect': reverse('perfil')})
            messages.success(request, 'Datos actualizados correctamente.')
            return redirect('perfil')

        if action == 'change_password':
            # Map POST parameters to native PasswordChangeForm names
            post_data = {
                'old_password': request.POST.get('actual'),
                'new_password1': request.POST.get('nueva'),
                'new_password2': request.POST.get('confirmar'),
            }
            form = PasswordChangeForm(user=user, data=post_data)

            if not form.is_valid():
                errors = {}
                for field, error_list in form.errors.items():
                    if field == 'old_password':
                        errors['actual'] = error_list[0]
                    elif field in ('new_password1', 'new_password2'):
                        errors['nueva'] = error_list[0]
                    else:
                        errors[field] = error_list[0]

                if is_ajax:
                    first_error = next(iter(errors.values())) if errors else 'Error al validar datos.'
                    return JsonResponse({'ok': False, 'error': first_error, 'errors': errors}, status=400)
                return render(request, 'perfil.html', {
                    'field_errors': errors,
                    'pedidos': pedidos_usuario,
                    'security_info': security_info,
                    'direccion': direccion,
                })

            form.save()
            update_session_auth_hash(request, user)

            if is_ajax:
                return JsonResponse({'ok': True, 'message': 'Contraseña actualizada con éxito.', 'redirect': reverse('perfil')})
            messages.success(request, 'Contraseña actualizada con éxito.')
            return redirect('perfil')

    return render(request, 'perfil.html', {
        'pedidos': pedidos_usuario,
        'security_info': security_info,
        'direccion': direccion,
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

    total_productos = Producto.objects.filter(estado='ACTIVO').count()

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
        nombre=F('variante__producto__nombre')
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