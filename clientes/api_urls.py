from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'clientes', views.ClienteViewSet, basename='cliente')
router.register(r'direcciones', views.DireccionUsuarioViewSet, basename='direccionusuario')
router.register(r'metodos-pago', views.MetodoPagoClienteViewSet, basename='metodo-pago')

urlpatterns = [
    path('', include(router.urls)),
]
