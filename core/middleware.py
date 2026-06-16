from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.cache import patch_cache_control, patch_vary_headers


class AnonymousRouteGuardMiddleware:
    """Allow anonymous users only on explicitly public routes."""

    PUBLIC_EXACT_PATHS = {
        '/',
        '/productos.html',
        '/detalle_producto.html',
        '/favicon.ico',
    }

    PUBLIC_PREFIXES = (
        '/static/',
        '/media/',
        '/login/',
        '/logout/',
        '/registro/',
        '/password/',
        '/productos/',
        '/api/csrf-token/',
        '/api/productos-buscar/',
        '/api/productos/',
        '/api/categorias/',
        '/api/marcas/',
        '/api/colores/',
        '/api/unidades-medida/',
        '/api/inventario-productos/',
    )

    def _has_force_authentication(self, request):
        return (
            getattr(request, '_force_auth_user', None) is not None
            or getattr(request, '_force_auth_token', None) is not None
        )

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_public_path(self, path: str) -> bool:
        if path in self.PUBLIC_EXACT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES)

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False) and not self._has_force_authentication(request) and not self._is_public_path(request.path):
            if request.path.startswith('/api/'):
                return JsonResponse({'ok': False, 'error': 'Autenticación requerida.'}, status=401)

            next_url = quote(request.get_full_path())
            login_redirect = f'/login/?next={next_url}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'redirect': login_redirect}, status=401)
            return redirect(login_redirect)

        return self.get_response(request)


class NoStoreAuthenticatedPagesMiddleware:
    """Prevent authenticated pages from being cached in browser history."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, 'user', None)
        if getattr(user, 'is_authenticated', False):
            patch_cache_control(
                response,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
                private=True,
                max_age=0,
            )
            patch_vary_headers(response, ['Cookie'])
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


class SecurityHeadersMiddleware:
    """Add baseline security headers for clickjacking/sniffing/privacy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), camera=(), microphone=(), payment=()')
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-site')

        return response
