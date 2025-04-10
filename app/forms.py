from django import forms
from .models import Receta, Ingrediente, TipoComida, Calendario, Familia
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


class CustomSignupForm(UserCreationForm):
    ACCION_FAMILIAR_CHOICES = (
        ('crear', 'Crear una nueva familia'),
        ('unirse', 'Unirte a una familia existente'),
    )
    accion_familiar = forms.ChoiceField(
        choices=ACCION_FAMILIAR_CHOICES,
        widget=forms.RadioSelect,
        label="¿Qué acción familiar deseas realizar?"
    )
    # Si se crea una familia, se solicita un nombre.
    nombre_familia = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre para la nueva familia"
    )
    # Si se va a unir, se ofrece un listado de familias existentes.
    familia_existente = forms.ModelChoiceField(
        queryset=Familia.objects.all(),
        required=False,
        label="Familia a la que deseas unirte"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields  # Por defecto 'username', 'password1' y 'password2'

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get("accion_familiar")
        nombre = cleaned_data.get("nombre_familia")
        familia_existente = cleaned_data.get("familia_existente")
        if accion == 'crear' and not nombre:
            self.add_error('nombre_familia', "Debes proporcionar un nombre para la nueva familia.")
        if accion == 'unirse' and not familia_existente:
            self.add_error('familia_existente', "Debes seleccionar una familia a la que unirte.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit)
        accion = self.cleaned_data.get("accion_familiar")
        if accion == 'crear':
            # Crea una nueva familia y añade el usuario
            familia = Familia.objects.create(nombre=self.cleaned_data.get("nombre_familia"))
            familia.miembros.add(user)
        elif accion == 'unirse':
            familia = self.cleaned_data.get("familia_existente")
            familia.miembros.add(user)
        return user



class ChangeFamilyForm(forms.Form):
    ACCION_CHOICES = (
        ('crear', 'Crear una nueva familia'),
        ('unirse', 'Unirse a una familia existente'),
    )
    accion_familiar = forms.ChoiceField(
        choices=ACCION_CHOICES,
        widget=forms.RadioSelect,
        label="¿Qué acción deseas realizar?"
    )
    nombre_familia = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre para la nueva familia"
    )
    # Cambiamos de ModelChoiceField a CharField para que el usuario escriba el nombre de la familia existente.
    familia_existente = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre de la familia a la que deseas unirte"
    )

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get("accion_familiar")
        if accion == 'crear':
            if not cleaned_data.get("nombre_familia"):
                self.add_error('nombre_familia', "Debes proporcionar el nombre para la nueva familia.")
        elif accion == 'unirse':
            nombre = cleaned_data.get("familia_existente", "").strip()
            if not nombre:
                self.add_error('familia_existente', "Debes escribir el nombre de la familia a la que deseas unirte.")
            else:
                # Verificamos que la familia exista (búsqueda insensible a mayúsculas)
                if not Familia.objects.filter(nombre__iexact=nombre).exists():
                    self.add_error('familia_existente', "La familia especificada no existe.")
        return cleaned_data