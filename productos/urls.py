from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'productos', views.ProductoViewSet)
router.register(r'categorias', views.CategoriaViewSet)
router.register(r'marcas', views.MarcaViewSet)
router.register(r'colores', views.ColorViewSet)
router.register(r'unidades-medida', views.UnidadMedidaViewSet)

urlpatterns = [
    path('productos/', views.productos_page, name='productos'),
    path('productos.html', views.productos_page, name='productos_html'),
    path('productos/detalle/<int:producto_id>/', views.detalle_producto_page, name='detalle_producto'),
    path('detalle_producto.html', views.detalle_producto_page_query, name='detalle_producto_html'),
    path('api/csrf-token/', views.csrf_token_api, name='api_csrf_token'),
    path('api/productos-buscar/', views.buscar_productos_api, name='api_productos_buscar'),
    path('catalogo/', views.catalogo_productos, name='catalogo_productos'),
    path('catalogo/atributos/', views.catalogo_atributos, name='catalogo_atributos'),
    path('catalogos/', views.catalogo_atributos, name='catalogos_admin'),
    path('api/', include(router.urls)),
]