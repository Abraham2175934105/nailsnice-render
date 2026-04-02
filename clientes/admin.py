from django.contrib import admin
from .models import Cliente, ServicioCliente


class MinZeroAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield and db_field.get_internal_type() in {'IntegerField', 'PositiveIntegerField'}:
            formfield.widget.attrs.setdefault('min', 0)
        return formfield


@admin.register(Cliente)
class ClienteAdmin(MinZeroAdminMixin, admin.ModelAdmin):
    list_display = ('usuario', 'direccion', 'puntos_fidelidad')
    search_fields = ('usuario__email', 'usuario__nombre1', 'direccion')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Información del Cliente', {
            'fields': ('direccion', 'puntos_fidelidad')
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ServicioCliente)
class ServicioClienteAdmin(MinZeroAdminMixin, admin.ModelAdmin):
    list_display = ('cliente', 'canal_comunicacion', 'estado_ticket', 'fecha_contacto')
    list_filter = ('canal_comunicacion', 'estado_ticket', 'fecha_contacto')
    search_fields = ('cliente__usuario__email',)
    readonly_fields = ('fecha_contacto',)
