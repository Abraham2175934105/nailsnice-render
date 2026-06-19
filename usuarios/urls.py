from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configuración del espacio de nombres para reversión de URLs (reverse_lazy)
app_name = 'usuarios'

# 1. Enrutador para la API REST (Datos JSON)
router = DefaultRouter()
router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'roles', views.RolViewSet)
router.register(r'empleados', views.EmpleadoViewSet)

# 2. Definición combinada de Rutas (API + Pantallas de Interfaz HTML)
urlpatterns = [
    # Rutas heredadas de la API
    path('api/', include(router.urls)),
    
    # Nuevas rutas separadas para la interfaz administrativa de gestión (Server-Rendered HTML)
    path('gestion/administradores/', views.AdministradorListView.as_view(), name='admin_list'),
    path('gestion/empleados/', views.EmpleadoUIListView.as_view(), name='empleado_list'),
    path('gestion/crear/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('gestion/<int:id_usuario>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_edit'),
    path('gestion/<int:id_usuario>/estado/', views.alternar_estado_usuario_view, name='usuario_toggle_status'),
    # Password recovery endpoints (JSON)
    # Interfaz de recuperación (HTML)
    path('password-reset/', views.password_reset_request_page, name='password_reset_page'),
    path('password-reset/change/', views.password_reset_verify_page, name='password_reset_change_page'),

    # Password recovery endpoints (JSON)
    path('password-reset/request/', views.request_password_reset, name='password_reset_request'),
    path('password-reset/verify/', views.verify_password_reset, name='password_reset_verify'),
]