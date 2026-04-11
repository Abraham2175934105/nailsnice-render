from django.contrib.auth.decorators import login_required, user_passes_test
from functools import wraps

from usuarios.models import Rol


def _role_name(user):
    return str(getattr(getattr(user, 'id_rol', None), 'nombre', '') or '').strip().lower()


def is_admin_user(user):
    role = _role_name(user)
    return user.is_authenticated and (
        user.is_superuser
        or role in {Rol.ADMIN.lower(), 'admin', 'administrador'}
    )


def is_employee_user(user):
    return user.is_authenticated and _role_name(user) == Rol.EMPLEADO.lower()


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return login_required(user_passes_test(is_admin_user, login_url='/login/')(_wrapped_view))


def employee_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return login_required(user_passes_test(is_employee_user, login_url='/login/')(_wrapped_view))
