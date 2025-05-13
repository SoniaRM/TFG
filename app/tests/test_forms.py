from django.test import TestCase
from django.contrib.auth.models import User
from app.forms import (
    RecetaForm, IngredienteForm, ObjetivoDiarioForm,
    CustomUserCreationForm, CustomSignupForm,
    ChangeFamilyForm, ReenviarSolicitudForm
)
from app.models import Ingrediente, Familia, TipoComida, Receta

class FormsTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        TipoComida.objects.all().delete()
        cls.user = User.objects.create_user(username="testuser", password="12345")
        cls.familia = Familia.objects.create(nombre="FamiliaTest", administrador=cls.user)
        cls.familia.miembros.add(cls.user)
        cls.tipo_comida = TipoComida.objects.create(nombre="Almuerzo")

        cls.ingrediente = Ingrediente.objects.create(nombre="Lechuga", familia=cls.familia, frec=1)

    def test_receta_form_valid(self):
        form_data = {
            'nombre': 'Ensalada',
            'proteinas': 10,
            'carbohidratos': 20,
            'descripcion': 'Una rica ensalada',
            'combinable': True,
            'tipo_comida': [self.tipo_comida.id],
            'ingredientes': [self.ingrediente.id]
        }
        form = RecetaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_ingrediente_form_valid(self):
        form_data = {'nombre': 'Tomate', 'frec': 2}
        form = IngredienteForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_ingrediente_form_invalid_duplicate(self):
        Ingrediente.objects.create(nombre="Tomate", familia=self.familia, frec=2)
        form_data = {'nombre': 'Tomate', 'frec': 2}
        form = IngredienteForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_objetivo_diario_form_valid(self):
        form_data = {'objetivo_proteico': 50, 'objetivo_carbohidratos': 150}
        form = ObjetivoDiarioForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_user_creation_form_valid(self):
        form_data = {
            'username': 'newuser',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_signup_form_valid_crear_familia(self):
        form_data = {
            'username': 'newuser',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'accion_familiar': 'crear',
            'nombre_familia': 'NuevaFamilia'
        }
        form = CustomSignupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_signup_form_invalid_unirse_no_codigo(self):
        form_data = {
            'username': 'newuser',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'accion_familiar': 'unirse',
            'familia_existente': ''
        }
        form = CustomSignupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('familia_existente', form.errors)

    def test_change_family_form_valid_create(self):
        form_data = {'accion_familiar': 'crear', 'nombre_familia': 'OtraFamilia'}
        form = ChangeFamilyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_change_family_form_invalid_join_wrong_code(self):
        form_data = {'accion_familiar': 'unirse', 'codigo_invitacion': 'WRONGCODE'}
        form = ChangeFamilyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('codigo_invitacion', form.errors)

    def test_reenviar_solicitud_form_invalid(self):
        form_data = {'familia_existente': 'NOEXISTE'}
        form = ReenviarSolicitudForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('familia_existente', form.errors)

    def test_reenviar_solicitud_form_valid(self):
        form_data = {'familia_existente': self.familia.codigo_invitacion}
        form = ReenviarSolicitudForm(data=form_data)
        self.assertTrue(form.is_valid())
