from django import forms
from .models import Receta, Ingrediente, TipoComida

class RecetaForm(forms.ModelForm):
    nombre = forms.CharField(max_length=100)
    proteinas = forms.IntegerField()

    class Meta:
        model = Receta
        fields = ['nombre', 'tipo_comida', 'proteinas', 'ingredientes']
        widgets = {
            'tipo_comida': forms.CheckboxSelectMultiple,
            'ingredientes': forms.CheckboxSelectMultiple,
        }

class IngredienteForm(forms.ModelForm):
    nombre = forms.CharField(max_length=100)
    frec = forms.IntegerField()

    class Meta:
        model = Ingrediente
        fields = ['nombre', 'frec']