from django.contrib import admin
from .models import (
    TipoServicio, CategoriaServicio, Servicio, 
    EmpleadoServicio, Agendamiento, HistorialEstadoAgendamiento
)


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo')
    fieldsets = (
        ('Información', {
            'fields': ('codigo', 'nombre')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )


@admin.register(CategoriaServicio)
class CategoriaServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_servicio', 'categoria_servicio', 'duracion_minutos', 'precio_base', 'activo')
    list_filter = ('tipo_servicio', 'categoria_servicio', 'activo')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('creado_en',)
    fieldsets = (
        ('Clasificación', {
            'fields': ('tipo_servicio', 'categoria_servicio')
        }),
        ('Información del Servicio', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Precios y Duración', {
            'fields': ('precio_base', 'duracion_minutos')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('creado_en',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmpleadoServicio)
class EmpleadoServicioAdmin(admin.ModelAdmin):
    list_display = ('get_empleado_email', 'servicio', 'get_duracion', 'get_precio', 'activo')
    list_filter = ('activo', 'servicio')
    search_fields = ('empleado__usuario__correo', 'servicio__nombre')
    fieldsets = (
        ('Asignación', {
            'fields': ('empleado', 'servicio')
        }),
        ('Personalización (opcional)', {
            'fields': ('duracion_personalizada_minutos', 'precio_personalizado'),
            'description': 'Dejar vacío para usar los valores del servicio'
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )

    def get_empleado_email(self, obj):
        return obj.empleado.usuario.correo
    get_empleado_email.short_description = 'Empleado'

    def get_duracion(self, obj):
        return obj.duracion_personalizada_minutos or f"Default ({obj.servicio.duracion_minutos} min)"
    get_duracion.short_description = 'Duración'

    def get_precio(self, obj):
        return obj.precio_personalizado or f"Default (${obj.servicio.precio_base})"
    get_precio.short_description = 'Precio'


@admin.register(Agendamiento)
class AgendamientoAdmin(admin.ModelAdmin):
    list_display = ('get_cliente_email', 'servicio', 'inicia_en', 'estado', 'get_empleado_email')
    list_filter = ('estado', 'inicia_en', 'servicio', 'canal')
    search_fields = ('cliente__usuario__correo', 'cliente__usuario__nombre', 'servicio__nombre', 'empleado__usuario__correo')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Cliente y Empleado', {
            'fields': ('cliente', 'empleado')
        }),
        ('Servicio', {
            'fields': ('servicio',)
        }),
        ('Fecha y Hora', {
            'fields': ('inicia_en', 'termina_en')
        }),
        ('Estado', {
            'fields': ('estado', 'canal')
        }),
        ('Observaciones', {
            'fields': ('notas',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

    def get_cliente_email(self, obj):
        return obj.cliente.usuario.correo
    get_cliente_email.short_description = 'Cliente'

    def get_empleado_email(self, obj):
        return obj.empleado.usuario.correo if obj.empleado else 'Sin asignar'
    get_empleado_email.short_description = 'Empleado'


@admin.register(HistorialEstadoAgendamiento)
class HistorialEstadoAgendamientoAdmin(admin.ModelAdmin):
    list_display = ('agendamiento', 'estado', 'cambiado_en', 'get_usuario')
    list_filter = ('estado', 'cambiado_en')
    search_fields = ('agendamiento__id_agendamiento', 'nota')
    readonly_fields = ('cambiado_en',)
    fieldsets = (
        ('Agendamiento', {
            'fields': ('agendamiento',)
        }),
        ('Cambio de Estado', {
            'fields': ('estado', 'nota')
        }),
        ('Auditoría', {
            'fields': ('cambiado_por', 'cambiado_en'),
            'classes': ('collapse',)
        }),
    )

    def get_usuario(self, obj):
        return obj.cambiado_por.correo if obj.cambiado_por else 'Sistema'
    get_usuario.short_description = 'Usuario'
