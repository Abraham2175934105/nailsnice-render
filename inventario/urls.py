from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import BodegaViewSet, SaldoInventarioViewSet
from .views import (
    lista_inventario,
    crear_producto,
    editar_producto,
    eliminar_producto,
    cargar_inventario_masivo,
    lista_movimientos,
    crear_movimiento,
)

router = DefaultRouter()
router.register(r'bodegas', BodegaViewSet, basename='bodega')
router.register(r'saldos', SaldoInventarioViewSet, basename='saldo-inventario')

urlpatterns = [
    # API REST
    path('api/', include(router.urls)),

    # Inventario (productos y saldos)
    path('', lista_inventario, name='lista_inventario'),
    path('crear/', crear_producto, name='crear_producto'),
    path('editar/<int:id>/', editar_producto, name='editar_producto'),
    path('eliminar/<int:id>/', eliminar_producto, name='eliminar_producto'),
    path('carga-masiva/', cargar_inventario_masivo, name='inventario_carga_masiva'),

    # Movimientos de inventario
    path('movimientos/', lista_movimientos, name='lista_movimientos'),
    path('movimientos/crear/', crear_movimiento, name='crear_movimiento'),
]