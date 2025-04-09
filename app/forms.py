from django import forms
from .models import Receta, Ingrediente, TipoComida, Calendario
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

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

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sobreescribir etiquetas (labels)
        self.fields['username'].label = "Nombre de usuario"
        self.fields['password1'].label = "Contraseña"
        self.fields['password2'].label = "Confirmar contraseña"

        # Remover help_text
        self.fields['username'].help_text = ""
        self.fields['password1'].help_text = ""
        self.fields['password2'].help_text = ""

        # Agregar clases de Bootstrap a los inputs
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})