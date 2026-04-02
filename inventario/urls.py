from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .api import ProductoMaquillajeViewSet

router = DefaultRouter()
router.register(r'inventario-productos', ProductoMaquillajeViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
