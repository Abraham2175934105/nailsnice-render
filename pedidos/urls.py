from django.urls import path
from . import views

urlpatterns = [
    # Admin
    path('', views.lista_pedidos, name='lista_pedidos'),
    path('crear/', views.crear_pedido, name='crear_pedido'),
    path('<int:id>/editar/', views.editar_pedido, name='editar_pedido'),
    path('<int:id>/eliminar/', views.eliminar_pedido, name='eliminar_pedido'),
    path('<int:id>/detalle/', views.detalle_pedido, name='detalle_pedido'),

    # Empleado
    path('mis-pedidos/', views.empleado_lista_pedidos, name='empleado_pedidos'),
    path('mis-pedidos/crear/', views.empleado_crear_pedido, name='empleado_crear_pedido'),
    path('mis-pedidos/<int:id>/editar/', views.empleado_editar_pedido, name='empleado_editar_pedido'),
    path('mis-pedidos/<int:id>/eliminar/', views.empleado_eliminar_pedido, name='empleado_eliminar_pedido'),

    # Carrito y checkout
    path('carrito/', views.cart_view, name='carrito'),
    path('carrito/agregar/<int:product_id>/', views.cart_add, name='cart_add'),
    path('carrito/actualizar/<int:product_id>/', views.cart_update, name='cart_update'),
    path('carrito/eliminar/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('factura/<int:pedido_id>/', views.invoice_view, name='factura'),
    path('factura/<int:pedido_id>/pdf/', views.invoice_pdf_view, name='factura_pdf'),
]