from django.contrib import admin
from inventario.models import Bodega 

@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    pass
