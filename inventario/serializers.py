from rest_framework import serializers
from .models import Bodega, SaldoInventario

class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = '__all__'


class SaldoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaldoInventario
        fields = '__all__'