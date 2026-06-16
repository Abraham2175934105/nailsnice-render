from django.urls import include, path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('',                views.cliente_list,   name='cliente_list'),
    path('nuevo/',          views.cliente_create, name='cliente_create'),
    path('<int:pk>/',       views.cliente_detail, name='cliente_detail'),

    path('<int:cliente_pk>/direcciones/nueva/',
         views.direccion_create, name='direccion_create'),
    path('<int:cliente_pk>/direcciones/<int:pk>/editar/',
         views.direccion_update, name='direccion_update'),
    path('<int:cliente_pk>/direcciones/<int:pk>/eliminar/',
         views.direccion_delete, name='direccion_delete'),
]