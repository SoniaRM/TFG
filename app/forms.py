from django import forms
from .models import Receta, Ingrediente, TipoComida, Calendario, Familia, SolicitudUniónFamilia
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RecetaForm(forms.ModelForm):
    nombre = forms.CharField(max_length=100)
    proteinas = forms.IntegerField()
    carbohidratos = forms.IntegerField()
    descripcion = forms.CharField(
        label="Descripción (opcional)",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Añade aquí una descripción de tu receta...',
            'style': 'max-height:300px; resize:vertical; overflow-y:auto;'
        })
    )
    combinable = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Receta
        fields = ['nombre', 'tipo_comida', 'proteinas', 'carbohidratos', 'descripcion', 'combinable', 'ingredientes']
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
    
    def __init__(self, *args, user=None, **kwargs):
        # “extraemos” user si lo han pasado
        super().__init__(*args, **kwargs)
        self.user = user  # <-- guardamos el usuario

    
    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        familia = self.user.familias.first()
        if Ingrediente.objects.filter(
            nombre__iexact=nombre,
            familia=familia
        ).exists():
            raise forms.ValidationError("Ya existe un ingrediente con este nombre.")
        return nombre


class ObjetivoDiarioForm(forms.ModelForm):
    class Meta:
        model = Calendario
        fields = ['objetivo_proteico', 'objetivo_carbohidratos']
        widgets = {
            'objetivo_proteico': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'objetivo_carbohidratos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'objetivo_proteico': 'Objetivo diario de proteínas (g)',
            'objetivo_carbohidratos': 'Objetivo diario de carbohidratos (g)',
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
    nombre_familia = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre para la nueva familia"
    )
    familia_existente = forms.CharField(
        max_length=100,
        required=False,
        label="Código de invitación de la familia"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields  # 'username', 'password1', 'password2'

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get("accion_familiar")
        if accion == 'crear':
            if not cleaned_data.get("nombre_familia"):
                self.add_error('nombre_familia', "Debes proporcionar un nombre para la nueva familia.")
        elif accion == 'unirse':
            codigo = cleaned_data.get("familia_existente", "").strip()
            if not codigo:
                self.add_error('familia_existente', "Debes ingresar el código de invitación.")
            else:
                try:
                    familia = Familia.objects.get(codigo_invitacion__iexact=codigo)
                    cleaned_data["familia_object"] = familia
                except Familia.DoesNotExist:
                    self.add_error('familia_existente', "No se encontró una familia con ese código.")
        return cleaned_data

    def save(self, commit=True):
        # Guarda el usuario de manera normal
        user = super().save(commit)
        accion = self.cleaned_data.get("accion_familiar")
        if accion == 'crear':
            # Crea la nueva familia y añade al usuario
            familia, created = Familia.objects.get_or_create(
                nombre=self.cleaned_data.get("nombre_familia").strip().lower()
            )
            familia.miembros.add(user)
            if created:
                familia.administrador = user
                familia.save()
        elif accion == 'unirse':
            # En lugar de agregar el usuario directamente, crea una solicitud de unión
            familia = self.cleaned_data.get("familia_object")
            # Crea la solicitud con estado "pendiente"
            SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
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
    # Solo se usa si se crea una nueva familia.
    nombre_familia = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre para la nueva familia"
    )
    # Para unirse, se debe introducir el código de invitación
    codigo_invitacion = forms.CharField(
        max_length=8,
        required=False,
        label="Código de invitación de la familia"
    )

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get("accion_familiar")
        if accion == 'crear':
            if not cleaned_data.get("nombre_familia"):
                self.add_error('nombre_familia', "Debes proporcionar el nombre para la nueva familia.")
        elif accion == 'unirse':
            codigo = cleaned_data.get("codigo_invitacion", "").strip()
            if not codigo:
                self.add_error('codigo_invitacion', "Debes ingresar el código de invitación.")
            else:
                # Verifica que exista una familia con ese código (búsqueda insensible a mayúsculas)
                try:
                    familia = Familia.objects.get(codigo_invitacion__iexact=codigo)
                    cleaned_data['familia_unirse'] = familia  # Guardamos la familia encontrada
                except Familia.DoesNotExist:
                    self.add_error('codigo_invitacion', "No se encontró una familia con ese código.")
        return cleaned_data


class ReenviarSolicitudForm(forms.Form):
    familia_existente = forms.CharField(
        max_length=100,
        label="Código de invitación de la familia"
    )

    def clean_familia_existente(self):
        codigo = self.cleaned_data.get('familia_existente', '').strip()
        try:
            familia = Familia.objects.get(codigo_invitacion__iexact=codigo)
        except Familia.DoesNotExist:
            raise forms.ValidationError("No se encontró una familia con ese código.")
        return familia