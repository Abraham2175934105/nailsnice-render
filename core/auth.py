from django.contrib.auth.decorators import login_required, user_passes_test
from functools import wraps

from usuarios.models import Rol


def is_admin_user(user):
    return user.is_authenticated and (
        user.is_superuser
        or getattr(getattr(user, 'id_rol', None), 'nombre', '') == Rol.ADMIN
    )


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return login_required(user_passes_test(is_admin_user, login_url='/login/')(_wrapped_view))
