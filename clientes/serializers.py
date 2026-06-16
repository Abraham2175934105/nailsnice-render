from typing import Any
from rest_framework import serializers

from usuarios.models import RolAcceso, Usuario, UsuarioRol
from usuarios.serializers import UsuarioSerializer

from .models import (
    Cliente,
    CuentaFidelizacion,
    DireccionUsuario,
    LibroPuntos,
    MetodoPagoCliente,
    ProveedorPago,
    TipoMetodoPago,
)


# ---------------------------------------------------------------------------
# Auxiliares (solo lectura, usados como nested en otros serializadores)
# ---------------------------------------------------------------------------

class ProveedorPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProveedorPago
        fields = ['id_proveedor', 'codigo', 'nombre', 'activo']


class TipoMetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoMetodoPago
        fields = ['id_tipo_metodo', 'codigo', 'nombre', 'activo']


# ---------------------------------------------------------------------------
# Cliente  (tu código original + método update añadido)
# ---------------------------------------------------------------------------

class ClienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Cliente
        fields = [
            'usuario',
            'fecha_nacimiento',
            'acepta_fidelizacion',
            'creado_en',
            'actualizado_en',
        ]
        read_only_fields = ['creado_en', 'actualizado_en']

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        password = usuario_data.pop('password', None)

        # CORRECCIÓN: Casteamos temporalmente a Any para que Pylance reconozca create_user 
        # sin importar cómo estén definidos los stubs del Custom Manager de Usuarios
        manager: Any = Usuario.objects
        usuario = manager.create_user(password=password, **usuario_data)

        # Set rol to Cliente si no está proporcionado
        rol_cliente, _ = RolAcceso.objects.get_or_create(
            nombre='Cliente', defaults={'codigo': 'CLIENTE'}
        )
        UsuarioRol.objects.create(usuario=usuario, rol=rol_cliente)

        return Cliente.objects.create(usuario=usuario, **validated_data)

    def update(self, instance, validated_data):
        usuario_data = validated_data.pop('usuario', None)
        if usuario_data:
            for attr, value in usuario_data.items():
                setattr(instance.usuario, attr, value)
            instance.usuario.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# DireccionUsuario
# ---------------------------------------------------------------------------

class DireccionUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DireccionUsuario
        fields = [
            'id_direccion',
            'usuario',
            'tipo_direccion',
            'etiqueta',
            'nombre_destinatario',
            'linea1',
            'linea2',
            'ciudad',
            'departamento',
            'codigo_postal',
            'codigo_pais',
            'es_predeterminada_envio',
            'es_predeterminada_factura',
            'creado_en',
            'actualizado_en',
            # Las columnas GENERATED ALWAYS (id_usuario_envio_predeterminado,
            # id_usuario_factura_predeterminado) las calcula MySQL automáticamente;
            # no se exponen en la API para evitar escrituras accidentales.
        ]
        read_only_fields = [
            'id_direccion',
            'creado_en',
            'actualizado_en',
        ]

    def validate_tipo_direccion(self, value):
        """Refuerza el CHECK de la BD a nivel de serializador."""
        validos = {c[0] for c in DireccionUsuario.TIPO_CHOICES}
        if value not in validos:
            raise serializers.ValidationError(
                f"Valor inválido. Opciones: {', '.join(validos)}"
            )
        return value

    def validate_codigo_pais(self, value):
        if len(value) != 2:
            raise serializers.ValidationError(
                "codigo_pais debe tener exactamente 2 caracteres (ej. CO, US)."
            )
        return value.upper()


# ---------------------------------------------------------------------------
# MetodoPagoCliente  (solo lectura — tokens gestionados por la pasarela)
# ---------------------------------------------------------------------------

class MetodoPagoClienteSerializer(serializers.ModelSerializer):
    tipo_metodo = TipoMetodoPagoSerializer(read_only=True)
    proveedor = ProveedorPagoSerializer(read_only=True)

    class Meta:
        model = MetodoPagoCliente
        fields = [
            'id_metodo_pago',
            'cliente',
            'tipo_metodo',
            'proveedor',
            'etiqueta_mascara',
            'nombre_titular',
            'ultimos4',
            'mes_expiracion',
            'anio_expiracion',
            'es_predeterminado',
            'estado',
            'creado_en',
            'actualizado_en',
            # 'token' excluido intencionalmente: dato sensible gestionado
            # por la pasarela, no debe exponerse en la API admin.
        ]
        read_only_fields = [
            'id_metodo_pago',
            'cliente',
            'tipo_metodo',
            'proveedor',
            'etiqueta_mascara',
            'nombre_titular',
            'ultimos4',
            'mes_expiracion',
            'anio_expiracion',
            'es_predeterminado',
            'estado',
            'creado_en',
            'actualizado_en',
        ]


# ---------------------------------------------------------------------------
# Fidelización  (solo lectura — los movimientos los genera el sistema)
# ---------------------------------------------------------------------------

class LibroPuntosSerializer(serializers.ModelSerializer):
    tipo_origen_display = serializers.CharField(
        source='get_tipo_origen_display', read_only=True
    )
    creado_por_correo = serializers.SerializerMethodField()

    class Meta:
        model = LibroPuntos
        fields = [
            'id_movimiento_puntos',
            'pedido_id',
            'tipo_origen',
            'tipo_origen_display',
            'puntos_delta',
            'descripcion',
            'creado_por',
            'creado_por_correo',
            'creado_en',
        ]
        read_only_fields = fields

    def get_creado_por_correo(self, obj):
        if obj.creado_por:
            return getattr(obj.creado_por, 'correo', str(obj.creado_por))
        return None


class CuentaFidelizacionSerializer(serializers.ModelSerializer):
    movimientos = LibroPuntosSerializer(
        source='cliente.movimientos_puntos',
        many=True,
        read_only=True,
    )

    class Meta:
        model = CuentaFidelizacion
        fields = [
            'puntos_actuales',
            'total_ganados',
            'total_redimidos',
            'actualizado_en',
            'movimientos',
        ]
        read_only_fields = fields