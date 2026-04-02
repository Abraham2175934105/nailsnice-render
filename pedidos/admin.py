from django.contrib import admin

from .models import DetallePedido, Pedido, Pedidos


@admin.register(Pedidos)
class PedidosLegacyAdmin(admin.ModelAdmin):
	list_display = ('id', 'usuario', 'producto', 'cantidad', 'precio', 'fecha', 'is_active')
	search_fields = ('usuario', 'producto', 'direccion')
	list_filter = ('is_active', 'fecha')


class DetallePedidoInline(admin.TabularInline):
	model = DetallePedido
	extra = 0
	readonly_fields = ('producto', 'cantidad', 'precio_unitario')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'usuario', 'metodo_pago', 'estado', 'total', 'creado_en')
	search_fields = ('usuario__email', 'direccion_envio')
	list_filter = ('estado', 'metodo_pago', 'creado_en')
	inlines = [DetallePedidoInline]


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'pedido', 'producto', 'cantidad', 'precio_unitario')
	search_fields = ('pedido__usuario__email', 'producto__nombre')

# Register your models here.
