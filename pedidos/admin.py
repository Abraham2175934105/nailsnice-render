from django.contrib import admin

from .models import PedidoVenta, DetallePedidoVenta


class DetallePedidoInline(admin.TabularInline):
	model = DetallePedidoVenta
	extra = 0

@admin.register(PedidoVenta)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id_pedido', 'cliente', 'estado', 'monto_total', 'creado_en')
	search_fields = ('cliente__usuario__correo', 'numero_pedido')
	list_filter = ('estado', 'creado_en')
	inlines = [DetallePedidoInline]


@admin.register(DetallePedidoVenta)
class DetallePedidoAdmin(admin.ModelAdmin):
	pass

# Register your models here.
