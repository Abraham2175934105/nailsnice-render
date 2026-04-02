from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tipo-servicios', views.TipoServicioViewSet)
router.register(r'servicios', views.ServicioViewSet)
router.register(r'agendamientos', views.AgendamientoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]