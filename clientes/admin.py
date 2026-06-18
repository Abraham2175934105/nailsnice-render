from django.contrib import admin
from .models import Cliente


class MinZeroAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield and db_field.get_internal_type() in {'IntegerField', 'PositiveIntegerField'}:
            formfield.widget.attrs.setdefault('min', 0)
        return formfield


@admin.register(Cliente)
class ClienteAdmin(MinZeroAdminMixin, admin.ModelAdmin):
    list_display = ('usuario', 'acepta_fidelizacion')
    search_fields = ('usuario__correo', 'usuario__nombre', 'usuario__apellido')
    readonly_fields = ('creado_en', 'actualizado_en')
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Información del Cliente', {
            'fields': ('acepta_fidelizacion',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

