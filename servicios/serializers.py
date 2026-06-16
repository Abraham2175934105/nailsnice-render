from rest_framework import serializers
from .models import (
    TipoServicio, CategoriaServicio, Servicio, 
    EmpleadoServicio, Agendamiento, HistorialEstadoAgendamiento
)
from clientes.models import Cliente
from usuarios.models import Empleado


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoServicio
        fields = ['id_tipo_servicio', 'codigo', 'nombre', 'activo']


class CategoriaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaServicio
        fields = ['id_categoria_servicio', 'nombre', 'descripcion', 'activo']


class ServicioSerializer(serializers.ModelSerializer):
    # Lectura estructurada
    tipo_servicio = TipoServicioSerializer(read_only=True)
    categoria_servicio = CategoriaServicioSerializer(read_only=True)
    
    # Escritura por ID
    tipo_servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoServicio.objects.all(), source='tipo_servicio', write_only=True
    )
    categoria_servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=CategoriaServicio.objects.all(), source='categoria_servicio', write_only=True
    )
    
    class Meta:
        model = Servicio
        fields = [
            'id_servicio', 'nombre', 'descripcion', 'tipo_servicio', 'tipo_servicio_id',
            'categoria_servicio', 'categoria_servicio_id', 'duracion_minutos', 'precio_base', 'activo', 'creado_en'
        ]


class EmpleadoServicioSerializer(serializers.ModelSerializer):
    empleado_correo = serializers.SerializerMethodField()
    servicio = ServicioSerializer(read_only=True)
    duracion = serializers.SerializerMethodField()
    precio = serializers.SerializerMethodField()
    
    # Soporte de escritura para asignaciones
    empleado_id = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(), source='empleado', write_only=True
    )
    servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(), source='servicio', write_only=True
    )
    
    class Meta:
        model = EmpleadoServicio
        fields = [
            'empleado_id', 'servicio_id', 'empleado_correo', 'servicio', 'duracion',
            'precio', 'activo'
        ]
    
    def get_empleado_correo(self, obj):
        try:
            return obj.empleado.usuario.correo
        except AttributeError:
            return None
    
    def get_duracion(self, obj):
        if obj.duracion_personalizada_minutos:
            return obj.duracion_personalizada_minutos
        return obj.servicio.duracion_minutos
    
    def get_precio(self, obj):
        if obj.precio_personalizado:
            return str(obj.precio_personalizado)
        return str(obj.servicio.precio_base)


class HistorialEstadoAgendamientoSerializer(serializers.ModelSerializer):
    usuario_correo = serializers.SerializerMethodField()
    
    class Meta:
        model = HistorialEstadoAgendamiento
        fields = [
            'id_historial_estado_agendamiento', 'agendamiento', 'estado',
            'usuario_correo', 'nota', 'cambiado_en'
        ]
    
    def get_usuario_correo(self, obj):
        return obj.cambiado_por.correo if obj.cambiado_por else 'Sistema'


class AgendamientoSerializer(serializers.ModelSerializer):
    cliente_correo = serializers.SerializerMethodField()
    empleado_correo = serializers.SerializerMethodField()
    servicio = ServicioSerializer(read_only=True)
    historial_estados = HistorialEstadoAgendamientoSerializer(many=True, read_only=True)
    
    # Campos obligatorios para permitir la creación exitosa de citas (POST)
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(), source='cliente', write_only=True
    )
    empleado_id = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(), source='empleado', write_only=True
    )
    servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(), source='servicio', write_only=True
    )
    
    class Meta:
        model = Agendamiento
        fields = [
            'id_agendamiento', 'cliente_id', 'empleado_id', 'servicio_id',
            'cliente_correo', 'empleado_correo', 'servicio',
            'estado', 'inicia_en', 'termina_en', 'canal', 'notas',
            'creado_en', 'actualizado_en', 'historial_estados'
        ]
    
    def get_cliente_correo(self, obj):
        try:
            return obj.cliente.usuario.correo
        except AttributeError:
            return "N/A"
    
    def get_empleado_correo(self, obj):
        try:
            return obj.empleado.usuario.correo if obj.empleado else 'Sin asignar'
        except AttributeError:
            return "Sin asignar"