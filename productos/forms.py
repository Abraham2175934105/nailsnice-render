from django import forms

from .models import CategoriaCatalogo, SubcategoriaCatalogo, MarcaCatalogo


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriaCatalogo
        fields = ['nombre', 'slug', 'descripcion', 'activo']


class SubcategoriaForm(forms.ModelForm):
    class Meta:
        model = SubcategoriaCatalogo
        fields = ['categoria', 'nombre', 'slug', 'descripcion', 'activo']


class MarcaForm(forms.ModelForm):
    class Meta:
        model = MarcaCatalogo
        fields = ['nombre', 'descripcion', 'activo']
