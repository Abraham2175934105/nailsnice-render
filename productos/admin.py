from django.contrib import admin
from .models import Categoria, Marca, Color, UnidadMedida, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre_categoria',)
    search_fields = ('nombre_categoria',)

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre_marca',)
    search_fields = ('nombre_marca',)

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('nombre_color',)
    search_fields = ('nombre_color',)

@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('nombre_medida',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'id_categoria', 'id_marca', 'estado_producto', 'creado_en')
    list_filter = ('estado_producto', 'id_categoria', 'id_marca', 'creado_en')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Información del Producto', {
            'fields': ('nombre', 'descripcion', 'precio', 'imagen')
        }),
        ('Clasificación', {
            'fields': ('id_categoria', 'id_marca', 'id_color', 'id_unidad_medida')
        }),
        ('Estado', {
            'fields': ('estado_producto',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
