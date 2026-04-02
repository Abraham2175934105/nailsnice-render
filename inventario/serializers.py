from rest_framework import serializers
from .models import ProductoMaquillaje


class ProductoMaquillajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoMaquillaje
        fields = [
            'id_inventario',
            'nombre',
            'descripcion',
            'marca',
            'precio',
            'stock',
            'imagen',
            'estado',
            'fecha_ingreso',
            'cantidad',
        ]
