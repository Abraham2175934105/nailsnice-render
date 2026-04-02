from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pedidos', views.PedidoViewSet)
router.register(r'pedido-productos', views.PedidoProductoViewSet)
router.register(r'ventas', views.VentaViewSet)
router.register(r'detalle-ventas', views.DetalleVentaViewSet)
router.register(r'metodos-pago', views.MetodoPagoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]