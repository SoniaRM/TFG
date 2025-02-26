from django import forms
from .models import Ingrediente

class IngredienteForm(forms.ModelForm):
    nombre = forms.CharField(max_length=100)
    frec = forms.IntegerField()
    
    class Meta:
        model = Ingrediente
        fields = ['nombre', 'frec']