from decimal import Decimal
from django.conf import settings
from django.db import models


class MarcaCatalogo(models.Model):
    id_marca = models.BigAutoField(primary_key=True, db_column='id_marca')
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marca_catalogo'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CategoriaCatalogo(models.Model):
    id_categoria = models.BigAutoField(primary_key=True, db_column='id_categoria')
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categoria_catalogo'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class SubcategoriaCatalogo(models.Model):
    id_subcategoria = models.BigAutoField(primary_key=True, db_column='id_subcategoria')
    categoria = models.ForeignKey(
        CategoriaCatalogo,
        db_column='id_categoria',
        on_delete=models.RESTRICT,
        related_name='subcategorias',
    )
    nombre = models.CharField(max_length=100, db_index=True)
    slug = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subcategoria_catalogo'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id_producto = models.BigAutoField(primary_key=True, db_column='id_producto')
    subcategoria = models.ForeignKey(
        SubcategoriaCatalogo,
        db_column='id_subcategoria',
        on_delete=models.RESTRICT,
        related_name='productos',
    )
    marca = models.ForeignKey(
        MarcaCatalogo,
        db_column='id_marca',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
    )
    nombre = models.CharField(max_length=160, db_index=True)
    slug = models.CharField(max_length=180, unique=True)
    descripcion_corta = models.CharField(max_length=255, null=True, blank=True)
    descripcion_larga = models.TextField(null=True, blank=True)
    descripcion_tecnica = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO', db_index=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='creado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='productos_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'producto'
        managed = True
        ordering = ['-creado_en']

    def __str__(self):
        return self.nombre


class VarianteProducto(models.Model):
    id_variante = models.BigAutoField(primary_key=True, db_column='id_variante')
    producto = models.ForeignKey(
        Producto,
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='variantes',
    )
    sku = models.CharField(max_length=80, unique=True)
    codigo_barras = models.CharField(max_length=80, null=True, blank=True, unique=True)
    nombre_variante = models.CharField(max_length=140, null=True, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    # CORRECCIÓN SENIOR: Se cambia default=0 por Decimal('0.00') para satisfacer estrictamente a Pylance
    costo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    codigo_moneda = models.CharField(max_length=3, default='COP')
    peso_gramos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'variante_producto'
        managed = True
        ordering = ['sku']

    def __str__(self):
        return self.sku


class ImagenProducto(models.Model):
    id_imagen = models.BigAutoField(primary_key=True, db_column='id_imagen')
    producto = models.ForeignKey(
        Producto,
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='imagenes',
    )
    variante = models.ForeignKey(
        VarianteProducto,
        db_column='id_variante',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='imagenes',
    )
    ruta_almacenamiento = models.CharField(max_length=255)
    texto_alternativo = models.CharField(max_length=180, null=True, blank=True)
    orden = models.IntegerField(default=0)
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'imagen_producto'
        managed = True
        ordering = ['orden', 'id_imagen']

    def __str__(self):
        return self.ruta_almacenamiento


class AtributoDefinicion(models.Model):
    id_atributo = models.BigAutoField(primary_key=True, db_column='id_atributo')
    codigo = models.CharField(max_length=80, unique=True)
    nombre = models.CharField(max_length=120, unique=True)
    tipo_dato = models.CharField(max_length=20)
    etiqueta_unidad = models.CharField(max_length=30, null=True, blank=True)
    es_filtrable = models.BooleanField(default=True)
    es_eje_variante = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'atributo_definicion'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class OpcionAtributo(models.Model):
    id_opcion = models.BigAutoField(primary_key=True, db_column='id_opcion')
    atributo = models.ForeignKey(
        AtributoDefinicion,
        db_column='id_atributo',
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    codigo_opcion = models.CharField(max_length=80)
    etiqueta_opcion = models.CharField(max_length=120)
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'opcion_atributo'
        managed = True
        ordering = ['orden', 'id_opcion']

    def __str__(self):
        return self.etiqueta_opcion


class ReglaAtributoSubcategoria(models.Model):
    id_regla = models.BigAutoField(primary_key=True, db_column='id_regla')
    subcategoria = models.ForeignKey(
        SubcategoriaCatalogo,
        db_column='id_subcategoria',
        on_delete=models.CASCADE,
        related_name='reglas_atributo',
    )
    atributo = models.ForeignKey(
        AtributoDefinicion,
        db_column='id_atributo',
        on_delete=models.CASCADE,
        related_name='reglas_subcategoria',
    )
    es_requerido = models.BooleanField(default=False)
    es_filtrable = models.BooleanField(default=True)
    es_eje_variante = models.BooleanField(default=False)
    aplica_a_variantes = models.BooleanField(default=False)
    orden = models.IntegerField(default=0)

    class Meta:
        db_table = 'regla_atributo_subcategoria'
        managed = True
        ordering = ['orden', 'id_regla']


class ValorAtributoProducto(models.Model):
    id_valor_atributo_producto = models.BigAutoField(primary_key=True, db_column='id_valor_atributo_producto')
    producto = models.ForeignKey(
        Producto,
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='valores_atributo',
    )
    atributo = models.ForeignKey(
        AtributoDefinicion,
        db_column='id_atributo',
        on_delete=models.RESTRICT,
        related_name='valores_producto',
    )
    opcion = models.ForeignKey(
        OpcionAtributo,
        db_column='id_opcion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='valores_producto',
    )
    valor_texto = models.TextField(null=True, blank=True)
    valor_numero = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    valor_booleano = models.BooleanField(null=True)
    valor_fecha = models.DateField(null=True, blank=True)
    valor_json = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'valor_atributo_producto'
        managed = True
        ordering = ['-creado_en']


class ValorAtributoVariante(models.Model):
    id_valor_atributo_variante = models.BigAutoField(primary_key=True, db_column='id_valor_atributo_variante')
    variante = models.ForeignKey(
        VarianteProducto,
        db_column='id_variante',
        on_delete=models.CASCADE,
        related_name='valores_atributo',
    )
    atributo = models.ForeignKey(
        AtributoDefinicion,
        db_column='id_atributo',
        on_delete=models.RESTRICT,
        related_name='valores_variante',
    )
    opcion = models.ForeignKey(
        OpcionAtributo,
        db_column='id_opcion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='valores_variante',
    )
    valor_texto = models.CharField(max_length=255, null=True, blank=True)
    valor_numero = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    valor_booleano = models.BooleanField(null=True)
    valor_fecha = models.DateField(null=True, blank=True)
    valor_json = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True, db_column='actualizado_en')

    class Meta:
        db_table = 'valor_atributo_variante'
        managed = True
        ordering = ['-creado_en']