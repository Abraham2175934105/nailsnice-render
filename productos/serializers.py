from django.conf import settings
from rest_framework import serializers

from .models import (
    Producto,
    CategoriaCatalogo,
    SubcategoriaCatalogo,
    MarcaCatalogo,
    ImagenProducto,
)


class CategoriaCatalogoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_categoria', read_only=True)
    nombre_categoria = serializers.CharField(source='nombre', read_only=True)

    class Meta:
        model = CategoriaCatalogo
        fields = ['id', 'nombre_categoria', 'slug', 'descripcion', 'activo']


class SubcategoriaCatalogoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_subcategoria', read_only=True)
    nombre_subcategoria = serializers.CharField(source='nombre', read_only=True)

    class Meta:
        model = SubcategoriaCatalogo
        fields = ['id', 'nombre_subcategoria', 'slug', 'descripcion', 'activo', 'categoria']


class MarcaCatalogoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_marca', read_only=True)
    nombre_marca = serializers.CharField(source='nombre', read_only=True)

    class Meta:
        model = MarcaCatalogo
        fields = ['id', 'nombre_marca', 'descripcion', 'activo']


class ProductoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='id_producto', read_only=True)
    descripcion = serializers.SerializerMethodField()
    precio = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    imagen = serializers.SerializerMethodField()
    estado_producto = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    categoria = CategoriaCatalogoSerializer(read_only=True, source='subcategoria.categoria')
    marca = MarcaCatalogoSerializer(read_only=True)
    color = serializers.SerializerMethodField()
    unidad_medida = serializers.SerializerMethodField()
    id_categoria = serializers.SerializerMethodField()
    id_marca = serializers.SerializerMethodField()
    id_color = serializers.SerializerMethodField()
    id_inventario = serializers.SerializerMethodField()
    inventario_id = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'id_producto',
            'nombre',
            'slug',
            'descripcion',
            'precio',
            'stock',
            'imagen',
            'estado',
            'estado_producto',
            'categoria',
            'marca',
            'color',
            'unidad_medida',
            'id_categoria',
            'id_marca',
            'id_color',
            'id_inventario',
            'inventario_id',
            'creado_en',
            'actualizado_en',
        ]

    def _normalize_image_url(self, value):
        raw = str(value or '').strip().replace('\\', '/')
        if not raw:
            return None
        if raw.startswith('http://') or raw.startswith('https://'):
            return raw

        media_url = settings.MEDIA_URL or '/media/'
        media_base = '/' + media_url.strip('/') + '/'

        if raw.startswith('//'):
            raw = '/' + raw.lstrip('/')

        if raw.startswith(media_base):
            while raw.startswith(media_base):
                raw = raw[len(media_base):]
            raw = raw.lstrip('/')
            return f"{media_base}{raw}" if raw else None

        media_no_slash = media_base.lstrip('/')
        if raw.startswith(media_no_slash):
            raw = raw[len(media_no_slash):].lstrip('/')
            return f"{media_base}{raw}" if raw else None

        if raw.startswith('/'):
            return raw

        return f"{media_base}{raw}"

    def _to_absolute(self, url):
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request') if hasattr(self, 'context') else None
        return request.build_absolute_uri(url) if request else url

    def _iter_imagenes(self, obj):
        imagenes = getattr(obj, 'imagenes', None)
        if imagenes is None or not hasattr(imagenes, 'all'):
            return []
        return imagenes.all().order_by('-es_principal', 'orden', 'id_imagen')

    def _get_default_variante(self, obj):
        manager = getattr(obj, 'variantes', None)
        if manager is None or not hasattr(manager, 'all'):
            return None
        
        variantes = list(manager.all())
        if not variantes:
            return None
        activos = [v for v in variantes if getattr(v, 'activo', False)]
        source = activos or variantes
        return sorted(source, key=lambda v: getattr(v, 'precio', 0) or 0)[0]

    def _get_disponible(self, variante):
        if not variante:
            return 0
        saldo = getattr(variante, 'saldo_inventario', None)
        if not saldo:
            return 0
        return max(0, (getattr(saldo, 'cantidad_existencia', 0) or 0) - (getattr(saldo, 'cantidad_reservada', 0) or 0))

    def _normalize_estado(self, estado):
        raw = str(estado or '').strip().upper()
        if raw in {'ACTIVO', 'ACTIVA'}:
            return 'Activo'
        if raw in {'INACTIVO', 'INACTIVA'}:
            return 'Inactivo'
        if raw in {'DESCONTINUADO', 'DESCONTINUADA'}:
            return 'Descontinuado'
        return estado or 'Activo'

    def get_descripcion(self, obj):
        return obj.descripcion_corta or obj.descripcion_larga or obj.descripcion_tecnica or ''

    def get_precio(self, obj):
        variante = self._get_default_variante(obj)
        return str(variante.precio) if (variante and getattr(variante, 'precio', None)) else '0'

    def get_stock(self, obj):
        variante = self._get_default_variante(obj)
        return self._get_disponible(variante)

    def get_imagen(self, obj):
        sources = []
        for img in self._iter_imagenes(obj):
            if img.ruta_almacenamiento:
                sources.append(img.ruta_almacenamiento)

        if not sources:
            manager_variantes = getattr(obj, 'variantes', None)
            variantes = list(manager_variantes.all()) if (manager_variantes and hasattr(manager_variantes, 'all')) else []
            for variante in variantes:
                img_manager = getattr(variante, 'imagenes', None)
                imagenes = img_manager.all() if (img_manager and hasattr(img_manager, 'all')) else []
                for img in imagenes:
                    if img.ruta_almacenamiento:
                        sources.append(img.ruta_almacenamiento)
                if sources:
                    break

        for source in sources:
            normalized = self._normalize_image_url(source)
            if normalized:
                return self._to_absolute(normalized)
        return None

    def get_estado_producto(self, obj):
        return self._normalize_estado(obj.estado)

    def get_estado(self, obj):
        return self._normalize_estado(obj.estado)

    def get_color(self, obj):
        return None

    def get_content_type(self, obj):
        return None

    def get_unidad_medida(self, obj):
        return None

    def get_id_categoria(self, obj):
        subcategoria = getattr(obj, 'subcategoria', None)
        categoria = getattr(subcategoria, 'categoria', None) if subcategoria else None
        return getattr(categoria, 'id_categoria', None)

    def get_id_marca(self, obj):
        return getattr(obj.marca, 'id_marca', None) if getattr(obj, 'marca', None) else None

    def get_id_color(self, obj):
        return None

    def get_id_inventario(self, obj):
        variante = self._get_default_variante(obj)
        return getattr(variante, 'id_variante', None) if variante else None

    def get_inventario_id(self, obj):
        return self.get_id_inventario(obj)