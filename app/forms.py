from django import forms
from .models import Receta, Ingrediente, TipoComida, Calendario

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


class ObjetivoDiarioForm(forms.ModelForm):
    class Meta:
        model = Calendario
        fields = ['objetivo_proteico']
        widgets = {
            'objetivo_proteico': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'objetivo_proteico': 'Objetivo diario de proteínas (g)'
        }
