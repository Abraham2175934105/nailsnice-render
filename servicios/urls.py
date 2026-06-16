from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# API Routes
router.register(r'tipo-servicios', views.TipoServicioViewSet)
router.register(r'categorias-servicios', views.CategoriaServicioViewSet)
router.register(r'servicios', views.ServicioViewSet)
router.register(r'empleado-servicios', views.EmpleadoServicioViewSet)
router.register(r'agendamientos', views.AgendamientoViewSet)
router.register(r'historial-agendamientos', views.HistorialEstadoAgendamientoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    
    # ADMIN - Agendamientos
    path('agendamientos/', views.lista_agendamientos, name='lista_agendamientos'),
    path('agendamientos/crear/', views.crear_agendamiento, name='crear_agendamiento'),
    path('agendamientos/editar/<int:id>/', views.editar_agendamiento, name='editar_agendamiento'),
    path('agendamientos/eliminar/<int:id>/', views.eliminar_agendamiento, name='eliminar_agendamiento'),
    path('agendamientos/carga-masiva/', views.carga_masiva_agendamientos, name='agendamientos_carga_masiva'),
    
    # ADMIN - Servicios CRUD
    path('servicios/', views.lista_servicios, name='lista_servicios'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),
    path('servicios/editar/<int:id>/', views.editar_servicio, name='editar_servicio'),
    path('servicios/eliminar/<int:id>/', views.eliminar_servicio, name='eliminar_servicio'),
    
    # ADMIN - Asignación Empleado-Servicio
    path('empleado-servicios/', views.lista_empleado_servicios, name='lista_empleado_servicios'),
    path('empleado-servicios/crear/', views.crear_empleado_servicio, name='crear_empleado_servicio'),
    path('empleado-servicios/editar/<int:id>/', views.editar_empleado_servicio, name='editar_empleado_servicio'),
    path('empleado-servicios/eliminar/<int:id>/', views.eliminar_empleado_servicio, name='eliminar_empleado_servicio'),
    
    # EMPLEADO - Agendamientos
    path('empleado/agendamientos/', views.empleado_lista_agendamientos, name='empleado_agendamientos'),
    path('empleado/agendamientos/crear/', views.empleado_crear_agendamiento, name='empleado_crear_agendamiento'),
    path('empleado/agendamientos/editar/<int:id>/', views.empleado_editar_agendamiento, name='empleado_editar_agendamiento'),
    path('empleado/agendamientos/eliminar/<int:id>/', views.empleado_eliminar_agendamiento, name='empleado_eliminar_agendamiento'),
]