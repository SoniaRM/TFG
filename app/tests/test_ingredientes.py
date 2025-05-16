from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.models import Familia, Ingrediente, Receta

class IngredientesViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.familia = Familia.objects.create(nombre='TestFamilia', administrador=self.user)
        self.familia.miembros.add(self.user)
        self.client.login(username='testuser', password='12345')
        self.ingrediente = Ingrediente.objects.create(nombre="Zanahoria", familia=self.familia, frec=1)

    def test_listado_ingredientes(self):
        response = self.client.get(reverse('listado_ingredientes'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingredientes/listado_ingredientes.html')
        self.assertIn(self.ingrediente, response.context['ingredientes'])

    def test_detalle_ingrediente_get(self):
        response = self.client.get(reverse('detalle_ingrediente', args=[self.ingrediente.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingredientes/detalle_ingrediente.html')
        self.assertEqual(response.context['ingrediente'], self.ingrediente)

    def test_detalle_ingrediente_post_delete(self):
        response = self.client.post(reverse('detalle_ingrediente', args=[self.ingrediente.id]), {'delete': '1'})
        self.assertRedirects(response, reverse('listado_ingredientes'))
        self.assertFalse(Ingrediente.objects.filter(id=self.ingrediente.id).exists())

    def test_detalle_ingrediente_404_si_no_pertenece_a_familia(self):
        otra_familia = Familia.objects.create(nombre='OtraFam', administrador=self.user)
        ingrediente_otro = Ingrediente.objects.create(nombre="Ajo", familia=otra_familia, frec=1)
        response = self.client.get(reverse('detalle_ingrediente', args=[ingrediente_otro.id]))
        self.assertEqual(response.status_code, 404)

    def test_detalle_ingrediente_incluye_recetas(self):
        receta = Receta.objects.create(nombre="Sopa", familia=self.familia, proteinas=10, carbohidratos=20)
        receta.ingredientes.add(self.ingrediente)
        response = self.client.get(reverse('detalle_ingrediente', args=[self.ingrediente.id]))
        self.assertIn(receta, response.context['recetas'])

    def test_crear_ingrediente_post_invalido(self):
        data = {'nombre': '', 'frec': ''}
        response = self.client.post(reverse('crear_ingrediente'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'nombre', 'Este campo es obligatorio.')
        self.assertFormError(response, 'form', 'frec', 'Este campo es obligatorio.')
        self.assertFalse(Ingrediente.objects.filter(nombre='').exists())

    def test_crear_ingrediente_get(self):
        response = self.client.get(reverse('crear_ingrediente'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingredientes/crear_ingrediente.html')

    def test_crear_ingrediente_post_invalido(self):
        data = {'nombre': '', 'frec': ''}
        response = self.client.post(reverse('crear_ingrediente'), data)
        form = response.context['form']  
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)
        self.assertIn('frec', form.errors)

    def test_editar_ingrediente_get(self):
        response = self.client.get(reverse('editar_ingrediente', args=[self.ingrediente.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingredientes/editar_ingrediente.html')
        self.assertEqual(response.context['ingrediente'], self.ingrediente)

    def test_editar_ingrediente_post_valido(self):
        from app.forms import IngredienteForm

        data = {'nombre': 'Zanahoria Modificada', 'frec': 2}
        form = IngredienteForm(data=data, instance=self.ingrediente, user=self.user)
        self.assertTrue(form.is_valid())
        form.save()

        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.nombre, 'Zanahoria Modificada')
    
    def test_editar_ingrediente_post_invalido(self):
        data = {'nombre': '', 'frec': ''}
        response = self.client.post(reverse('editar_ingrediente', args=[self.ingrediente.id]), data)
        form = response.context['form']  
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)
        self.assertIn('frec', form.errors)

    def test_editar_ingrediente_404_si_no_pertenece_a_familia(self):
        otra_familia = Familia.objects.create(nombre='OtraFam', administrador=self.user)
        ingrediente_otro = Ingrediente.objects.create(nombre="Puerro", familia=otra_familia, frec=1)
        response = self.client.get(reverse('editar_ingrediente', args=[ingrediente_otro.id]))
        self.assertEqual(response.status_code, 404)

    def test_crear_ingrediente_ajax_nombre_repetido_case_insensitive(self):
        data = {'nombre': 'zanahoria', 'frec': 1} 
        response = self.client.post(
            reverse('ingrediente_crear_ajax'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json())
        self.assertIn('nombre', response.json()['errors'])

    def test_crear_ingrediente_ajax_invalido_sin_nombre(self):
        data = {'nombre': '', 'frec': ''}
        response = self.client.post(
            reverse('ingrediente_crear_ajax'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json())
        self.assertIn('nombre', response.json()['errors'])
        self.assertIn('frec', response.json()['errors'])

    def test_crear_ingrediente_ajax_valido(self):
        data = {'nombre': 'Tomate', 'frec': 1}
        response = self.client.post(reverse('ingrediente_crear_ajax'), data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('id', response.json())
        self.assertIn('nombre', response.json())

    def test_crear_ingrediente_ajax_duplicado(self):
        data = {'nombre': 'Zanahoria', 'frec': 1}
        response = self.client.post(reverse('ingrediente_crear_ajax'), data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json())
        self.assertIn('nombre', response.json()['errors'])
