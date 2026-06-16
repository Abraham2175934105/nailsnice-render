from django.contrib import admin
from .models import Usuario, RolAcceso, PermisoAcceso, UsuarioRol, RolPermiso, Empleado

@admin.register(RolAcceso)
class RolAccesoAdmin(admin.ModelAdmin):
    # CORRECCIÓN SENIOR: Se quita 'creado_en' porque el modelo RolAcceso de la BD no lo posee
    list_display = ('id_rol', 'codigo', 'nombre', 'es_sistema')
    search_fields = ('codigo', 'nombre')
    list_filter = ('es_sistema',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # Ajustado a las columnas reales e indexadas de la tabla 3FN 'usuario'
    list_display = ('id_usuario', 'correo', 'nombre', 'apellido', 'estado', 'creado_en')
    list_filter = ('estado', 'creado_en')
    search_fields = ('correo', 'nombre', 'apellido')
    readonly_fields = ('creado_en', 'actualizado_en')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('correo', 'nombre', 'apellido', 'telefono')
        }),
        ('Permisos y Estado', {
            # CORRECCIÓN: Se quita 'is_active' (que es una property) y se manejan los campos físicos de la BD
            'fields': ('estado', 'is_staff', 'is_superuser')
        }),
        ('Fechas de Auditoría', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    # Mapeo idéntico para la tabla 'perfil_empleado'
    list_display = ('usuario', 'codigo_empleado', 'cargo', 'activo', 'creado_en')
    search_fields = ('usuario__correo', 'codigo_empleado', 'cargo')
    list_filter = ('activo', 'fecha_contratacion')
    readonly_fields = ('creado_en', 'actualizado_en')


# Registros adicionales de tablas relacionales/intermedias del sistema de seguridad
admin.site.register(PermisoAcceso)
admin.site.register(UsuarioRol)
admin.site.register(RolPermiso)