from django.conf import settings
from rest_framework import serializers
from .models import Producto, Categoria, Marca, Color, UnidadMedida

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = '__all__'

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = '__all__'

class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    # Los modelos usan `id_categoria`, `id_marca`, etc.; estos campos anidados
    # se exponen con nombres más amigables para el frontend.
    categoria = CategoriaSerializer(read_only=True, source='id_categoria')
    marca = MarcaSerializer(read_only=True, source='id_marca')
    color = ColorSerializer(read_only=True, source='id_color')
    unidad_medida = UnidadMedidaSerializer(read_only=True, source='id_unidad_medida')
    imagen = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = '__all__'

    def _image_candidates(self, image_field):
        if not image_field:
            return []

        candidates = []
        name = getattr(image_field, 'name', None)
        if name:
            candidates.append(name)

        try:
            url = image_field.url
            if url:
                candidates.append(url)
        except Exception:
            pass

        raw = str(image_field or '').strip()
        if raw:
            candidates.append(raw)

        deduped = []
        seen = set()
        for item in candidates:
            text = str(item or '').strip()
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
        return deduped

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

    def get_imagen(self, obj):
        sources = []
        sources.extend(self._image_candidates(getattr(obj, 'imagen', None)))

        inventario = getattr(obj, 'inventario', None)
        if inventario:
            sources.extend(self._image_candidates(getattr(inventario, 'imagen', None)))

        for source in sources:
            normalized = self._normalize_image_url(source)
            if normalized:
                return self._to_absolute(normalized)
        return None