from django.contrib import admin
from .models import TipoServicio, Servicio, Agendamiento

@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre_tipo',)

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre_servicio', 'tipo_servicio', 'precio_servicio', 'estado_servicio')
    list_filter = ('tipo_servicio', 'estado_servicio')
    search_fields = ('nombre_servicio', 'descripcion')
    fieldsets = (
        ('Información del Servicio', {
            'fields': ('nombre_servicio', 'descripcion', 'tipo_servicio')
        }),
        ('Precios y Duración', {
            'fields': ('precio_servicio', 'duracion_servicio', 'duracion_estimada')
        }),
        ('Clasificación y Estado', {
            'fields': ('categoria_servicio', 'estado_servicio')
        }),
    )

@admin.register(Agendamiento)
class AgendamientoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'servicio', 'fecha_agendamiento', 'hora_agendamiento', 'estado_agendamiento')
    list_filter = ('estado_agendamiento', 'fecha_agendamiento', 'servicio')
    search_fields = ('cliente__usuario__email', 'servicio__nombre_servicio')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Información del Agendamiento', {
            'fields': ('cliente', 'servicio', 'empleado')
        }),
        ('Fecha y Hora', {
            'fields': ('fecha_agendamiento', 'hora_agendamiento')
        }),
        ('Estado y Notas', {
            'fields': ('estado_agendamiento', 'notas')
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
