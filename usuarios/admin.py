from django.contrib import admin
from .models import Rol, Usuario, Empleado

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'creado_en')
    search_fields = ('nombre',)

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'nombre1', 'apellido1', 'id_rol', 'estado_usuario', 'creado_en')
    list_filter = ('id_rol', 'estado_usuario', 'creado_en')
    search_fields = ('email', 'nombre1', 'apellido1')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Información Personal', {
            'fields': ('email', 'nombre1', 'nombre2', 'apellido1', 'apellido2', 'telefono')
        }),
        ('Permisos y Estado', {
            'fields': ('id_rol', 'estado_usuario', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'id')
    search_fields = ('usuario__email',)
