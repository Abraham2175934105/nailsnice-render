from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from clientes.models import Cliente, DireccionUsuario, ProveedorPago
from inventario.models import SaldoInventario, TipoMovimientoInventario, MovimientoInventario, ItemMovimientoInventario
from core.audit import record_audit
from .models import (
    PedidoVenta,
    DetallePedidoVenta,
    HistorialEstadoPedido,
    TransaccionPago,
    CarritoCompra,
    ItemCarritoCompra,
)


def _build_audit_items(items):
    return [
        {'variante': item['variante'].id_variante, 'cantidad': item['cantidad']}
        for item in items
    ]


def _ensure_cliente(usuario):
    cliente, _ = Cliente.objects.get_or_create(usuario=usuario)
    return cliente


def _ensure_direccion(cliente, direccion_data, *, marcar_default=False):
    nombre_destinatario = (direccion_data.get('nombre_destinatario') or '').strip()
    if not nombre_destinatario:
        usuario = cliente.usuario
        nombre_destinatario = f"{getattr(usuario, 'nombre', '')} {getattr(usuario, 'apellido', '')}".strip() or usuario.correo

    direccion = DireccionUsuario.objects.create(
        usuario=cliente.usuario,
        tipo_direccion='ENVIO',
        etiqueta='Checkout',
        nombre_destinatario=nombre_destinatario[:120],
        linea1=(direccion_data.get('linea1') or '')[:160],
        linea2=(direccion_data.get('linea2') or '')[:160] or None,
        ciudad=(direccion_data.get('ciudad') or '')[:80],
        departamento=(direccion_data.get('departamento') or '')[:80] or None,
        codigo_postal=(direccion_data.get('codigo_postal') or '')[:20] or None,
        codigo_pais=(direccion_data.get('codigo_pais') or 'CO')[:2],
        es_predeterminada_envio=bool(marcar_default),
        es_predeterminada_factura=False,
    )
    return direccion


def _get_tipo_movimiento_salida():
    from django.db.models import Max
    obj = TipoMovimientoInventario.objects.filter(codigo='SALIDA_VENTA').first()
    if not obj:
        max_id = TipoMovimientoInventario.objects.aggregate(max_id=Max('id_tipo_movimiento'))['max_id']
        next_id = (max_id or 0) + 1
        obj, _ = TipoMovimientoInventario.objects.get_or_create(
            codigo='SALIDA_VENTA',
            defaults={
                'id_tipo_movimiento': next_id,
                'descripcion': 'Salida por Venta',
                'direccion': -1,
            }
        )
    return obj


def create_transaccion(pedido: PedidoVenta, metodo: str, usuario) -> TransaccionPago:
    """Crea la transacción asociada al pedido según el método de pago."""
    proveedor = None
    if metodo == 'tarjeta':
        proveedor = ProveedorPago.objects.filter(codigo='STRIPE').first()

    estado_tx = 'CAPTURADA' if metodo == 'contraentrega' else 'INICIADA'

    tx = TransaccionPago.objects.create(
        pedido=pedido,
        proveedor=proveedor,
        estado=estado_tx,
        monto=pedido.monto_total,
        codigo_moneda='COP',
    )
    return tx


def cambiar_estado_pedido(pedido: PedidoVenta, nuevo_estado: str, usuario=None, nota=None) -> PedidoVenta:
    """Cambia el estado de un pedido y registra el historial."""
    estados_validos = [e[0] for e in PedidoVenta.ESTADOS]
    if nuevo_estado not in estados_validos:
        raise ValidationError({'estado': f'Estado inválido: {nuevo_estado}'})

    if pedido.estado == nuevo_estado:
        return pedido

    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save(update_fields=['estado', 'actualizado_en'])

        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            cambiado_por=usuario,
            nota=nota or 'Cambio de estado',
        )

        record_audit(
            'pedidos.estado.cambio',
            usuario,
            'PedidoVenta',
            pedido.pk,
            {'nuevo_estado': nuevo_estado},
        )

    return pedido


def create_pedido_from_cart(usuario, items, direccion_data, metodo: str, *, cliente=None, estado='PENDIENTE_PAGO') -> PedidoVenta:
    if not items:
        raise ValidationError({'items': 'No hay items en el carrito.'})

    if cliente is None:
        cliente = _ensure_cliente(usuario)

    total = Decimal('0')
    for item in items:
        variante = item['variante']
        cantidad = int(item['cantidad'])
        saldo = SaldoInventario.objects.filter(variante=variante).first()
        disponible = 0
        if saldo:
            disponible = max(0, (saldo.cantidad_existencia or 0) - (saldo.cantidad_reservada or 0))
        if cantidad > disponible:
            raise ValidationError({'stock': f"Stock insuficiente para {variante.sku}."})
        total += Decimal(variante.precio) * cantidad

    tipo_salida = _get_tipo_movimiento_salida()
    if not tipo_salida:
        raise ValidationError({'inventario': 'No existe tipo de movimiento SALIDA_VENTA.'})

    with transaction.atomic():
        direccion_envio = _ensure_direccion(cliente, direccion_data)

        pedido = PedidoVenta.objects.create(
            numero_pedido='',
            cliente=cliente,
            estado=estado,
            subtotal=total,
            monto_envio=Decimal('0'),
            monto_impuesto=Decimal('0'),
            monto_descuento=Decimal('0'),
            monto_total=total,
            direccion_envio=direccion_envio,
        )

        # Recupera el numero_pedido generado por el trigger SQL
        pedido.refresh_from_db()

        # Registra el estado inicial en el historial
        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado=estado,
            cambiado_por=usuario,
            nota='Pedido creado',
        )

        movimientos = {}
        for item in items:
            variante = item['variante']
            cantidad = int(item['cantidad'])

            DetallePedidoVenta.objects.create(
                pedido=pedido,
                variante=variante,
                nombre_producto_snapshot=variante.producto.nombre,
                sku_snapshot=variante.sku,
                cantidad=cantidad,
                precio_unitario=variante.precio,
            )

            saldo = SaldoInventario.objects.filter(variante=variante).select_related('bodega').first()
            if not saldo:
                raise ValidationError({'inventario': f"No hay saldo para {variante.sku}."})

            movimiento = movimientos.get(saldo.bodega_id)
            if not movimiento:
                movimiento = MovimientoInventario.objects.create(
                    tipo_movimiento=tipo_salida,
                    bodega=saldo.bodega,
                    tipo_referencia='PEDIDO',
                    id_referencia=str(pedido.id_pedido),
                    creado_por=usuario,
                )
                movimientos[saldo.bodega_id] = movimiento

            ItemMovimientoInventario.objects.create(
                movimiento=movimiento,
                variante=variante,
                cantidad=cantidad,
                costo_unitario=variante.costo or Decimal('0'),
            )

        # Sincronizar carrito persistente en BD
        carrito_bd, _ = CarritoCompra.objects.get_or_create(
            cliente=cliente,
            estado='ACTIVO',
            defaults={'codigo_moneda': 'COP'},
        )
        for item in items:
            ItemCarritoCompra.objects.update_or_create(
                carrito=carrito_bd,
                variante=item['variante'],
                defaults={
                    'cantidad': item['cantidad'],
                    'precio_unitario_snapshot': item['variante'].precio,
                },
            )
        pedido.carrito = carrito_bd
        pedido.save(update_fields=['carrito', 'actualizado_en'])
        carrito_bd.estado = 'CONVERTIDO'
        carrito_bd.save(update_fields=['estado'])

        record_audit(
            'pedidos.create',
            usuario,
            'PedidoVenta',
            pedido.pk,
            {
                'total': str(total),
                'items': _build_audit_items(items),
                'metodo': metodo,
            },
        )

    return pedido