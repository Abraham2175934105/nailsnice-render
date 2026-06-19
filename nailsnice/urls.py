"""
URL configuration for Profesional Beauty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from core import views

from web import views as web_views
from pedidos.views import (
    lista_pedidos,
    crear_pedido,
    editar_pedido,
    eliminar_pedido,
    detalle_pedido,
    empleado_lista_pedidos,
    empleado_crear_pedido,
    empleado_editar_pedido,
    empleado_eliminar_pedido,
    cart_view,
    cart_add,
    cart_update,
    cart_remove,
    checkout_view,
    invoice_view,
    invoice_pdf_view,
)
from inventario import views as inventario_views
from servicios import views as servicios_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.profile_view, name='perfil'),
    path('password/forgot/', views.forgot_password_view, name='forgot_password'),
    path('password/verify/', views.verify_reset_code_view, name='verify_reset_code'),
    path('password/new/', views.new_password_view, name='new_password'),
    path('api/', views.home_api, name='api-home'),
    path('api/', include('clientes.api_urls')),
    path('', include('usuarios.urls')),
    path('', include('productos.urls')),
    path('', include('inventario.urls')),
    path('gestion/clientes/', include('clientes.urls')),
    path('', include('servicios.urls')),

    # CRUD Clientes (admin)
    path('clientes/', web_views.lista_clientes, name='lista_clientes'),
    path('clientes/crear/', web_views.crear_clientes, name='crear_cliente'),
    path('clientes/editar/<int:id>/', web_views.editar_clientes, name='editar_cliente'),
    path('clientes/eliminar/<int:id>/', web_views.eliminar_clientes, name='eliminar_cliente'),
    path('clientes/carga-masiva/', web_views.carga_masiva_clientes, name='clientes_carga_masiva'),

    # CRUD Clientes (app web)
    path('clientes_web/', web_views.lista_clientes, name='web_lista_clientes'),
    path('clientes_web/crear/', web_views.crear_clientes, name='web_crear_clientes'),
    path('clientes_web/editar/<int:id>/', web_views.editar_clientes, name='web_editar_clientes'),
    path('clientes_web/eliminar/<int:id>/', web_views.eliminar_clientes, name='web_eliminar_clientes'),

    # CRUD Pedidos (admin)
    path('pedidos/', lista_pedidos, name='lista_pedidos'),
    path('pedidos/crear/', crear_pedido, name='crear_pedido'),
    path('pedidos/editar/<int:id>/', editar_pedido, name='editar_pedido'),
    path('pedidos/eliminar/<int:id>/', eliminar_pedido, name='eliminar_pedido'),
    path('pedidos/<int:id>/detalle/', detalle_pedido, name='detalle_pedido'),

    # CRUD Empleado
    path('empleado/agendamientos/', servicios_views.empleado_lista_agendamientos, name='empleado_agendamientos'),
    path('empleado/agendamientos/crear/', servicios_views.empleado_crear_agendamiento, name='empleado_crear_agendamiento'),
    path('empleado/agendamientos/editar/<int:id>/', servicios_views.empleado_editar_agendamiento, name='empleado_editar_agendamiento'),
    path('empleado/agendamientos/eliminar/<int:id>/', servicios_views.empleado_eliminar_agendamiento, name='empleado_eliminar_agendamiento'),
    path('empleado/pedidos/', empleado_lista_pedidos, name='empleado_pedidos'),
    path('empleado/pedidos/crear/', empleado_crear_pedido, name='empleado_crear_pedido'),
    path('empleado/pedidos/editar/<int:id>/', empleado_editar_pedido, name='empleado_editar_pedido'),
    path('empleado/pedidos/eliminar/<int:id>/', empleado_eliminar_pedido, name='empleado_eliminar_pedido'),

    # Carrito y checkout
    path('carrito/', cart_view, name='carrito'),
    path('carrito/agregar/<int:product_id>/', cart_add, name='carrito_agregar'),
    path('carrito/actualizar/<int:product_id>/', cart_update, name='carrito_actualizar'),
    path('carrito/eliminar/<int:product_id>/', cart_remove, name='carrito_eliminar'),
    path('checkout/', checkout_view, name='checkout'),
    path('factura/<int:pedido_id>/', invoice_view, name='factura'),
    path('factura/<int:pedido_id>/pdf/', invoice_pdf_view, name='factura_pdf'),

    # CRUD Inventario
    path('inventario/', inventario_views.lista_inventario, name='lista_inventario'),
    path('inventario/crear/', inventario_views.crear_producto, name='crear_producto'),
    path('inventario/editar/<int:id>/', inventario_views.editar_producto, name='editar_producto'),
    path('inventario/eliminar/<int:id>/', inventario_views.eliminar_producto, name='eliminar_producto'),
    path('inventario/carga-masiva/', inventario_views.cargar_inventario_masivo, name='inventario_carga_masiva'),
    path('inventario/movimientos/', inventario_views.lista_movimientos, name='lista_movimientos'),
    path('inventario/movimientos/crear/', inventario_views.crear_movimiento, name='crear_movimiento'),
]

# Exponer las rutas de archivos multimedia en todos los entornos
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# En producción, si no se utiliza un backend de almacenamiento en la nube,
# servimos los archivos locales a través de la vista estática de Django.
if not settings.DEBUG:
    from django.views.static import serve
    from django.urls import re_path
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]