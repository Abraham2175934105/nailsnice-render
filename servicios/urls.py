from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tipo-servicios', views.TipoServicioViewSet)
router.register(r'servicios', views.ServicioViewSet)
router.register(r'agendamientos', views.AgendamientoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('agendamientos/', views.lista_agendamientos, name='lista_agendamientos'),
    path('agendamientos/crear/', views.crear_agendamiento, name='crear_agendamiento'),
    path('agendamientos/editar/<int:id>/', views.editar_agendamiento, name='editar_agendamiento'),
    path('agendamientos/eliminar/<int:id>/', views.eliminar_agendamiento, name='eliminar_agendamiento'),
    path('agendamientos/carga-masiva/', views.carga_masiva_agendamientos, name='agendamientos_carga_masiva'),
]