from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.models import Receta, Familia, Ingrediente, TipoComida

class RecetasViewTests(TestCase):

    def setUp(self):
        TipoComida.objects.all().delete()
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.familia = Familia.objects.create(nombre='FamiliaTest', administrador=self.user)
        self.familia.miembros.add(self.user)
        self.tipo = TipoComida.objects.create(nombre="Cena")
        self.ingrediente = Ingrediente.objects.create(nombre="Tomate", familia=self.familia, frec=1)
        self.client.login(username='testuser', password='12345')

    def test_listado_recetas(self):
        receta = Receta.objects.create(nombre="Ensalada", familia=self.familia, proteinas=10, carbohidratos=20)
        receta.ingredientes.add(self.ingrediente)
        receta.tipo_comida.add(self.tipo)
        response = self.client.get(reverse('listado_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recetas/listado_recetas.html')
        self.assertIn(receta, response.context['recetas'])

    def test_detalle_receta(self):
        receta = Receta.objects.create(nombre="Puré", familia=self.familia, proteinas=15, carbohidratos=30)
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)
        response = self.client.get(reverse('detalle_receta', args=[receta.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recetas/detalle_receta.html')
        self.assertEqual(response.context['receta'], receta)

    def test_detalle_receta_post_delete(self):
        receta = Receta.objects.create(nombre="Eliminar", familia=self.familia, proteinas=5, carbohidratos=10)
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)
        response = self.client.post(reverse('detalle_receta', args=[receta.id]), data={'delete': '1'})
        self.assertRedirects(response, reverse('listado_recetas'))
        self.assertFalse(Receta.objects.filter(id=receta.id).exists())

    def test_crear_receta_get(self):
        response = self.client.get(reverse('crear_receta'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recetas/crear_receta.html')

    def test_crear_receta_get_muestra_forms(self):
        response = self.client.get(reverse('crear_receta'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('ingrediente_form', response.context)
        self.assertTemplateUsed(response, 'recetas/crear_receta.html')

    def test_crear_receta_post_valido(self):
        data = {
            'nombre': 'Nueva Receta',
            'proteinas': 10,
            'carbohidratos': 20,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        response = self.client.post(reverse('crear_receta'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Receta.objects.filter(nombre='Nueva Receta').exists())
        self.assertTemplateUsed(response, 'recetas/crear_receta.html')
        self.assertTrue(response.context['exito'])
    
    def test_crear_receta_post_varios_ingredientes(self):
        ing2 = Ingrediente.objects.create(nombre="Patata", familia=self.familia, frec=1)
        data = {
            'nombre': 'Pisto',
            'proteinas': 12,
            'carbohidratos': 30,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id, ing2.id],
        }
        response = self.client.post(reverse('crear_receta'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Receta.objects.filter(nombre='Pisto').exists())
        self.assertTrue(response.context['exito'])
        self.assertIn('ingrediente_form', response.context)
    
    def test_crear_receta_post_nombre_vacio(self):
        data = {
            'nombre': '',
            'proteinas': 10,
            'carbohidratos': 20,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        response = self.client.post(reverse('crear_receta'), data)
        form = response.context['form']
        self.assertFormError(form, 'nombre', 'Este campo es obligatorio.')

    def test_editar_receta_get(self):
        receta = Receta.objects.create(nombre="Editar", familia=self.familia, proteinas=8, carbohidratos=18)
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)
        response = self.client.get(reverse('editar_receta', args=[receta.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recetas/editar_receta.html')
        self.assertEqual(response.context['receta'], receta)

    def test_crear_receta_post_proteina_negativa(self):
        data = {
            'nombre': 'Test Receta',
            'proteinas': -5,  # inválido
            'carbohidratos': 10,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        response = self.client.post(reverse('crear_receta'), data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('proteinas', form.errors)


    def test_editar_receta_post_valido(self):
        receta = Receta.objects.create(nombre="Editar Nombre", familia=self.familia, proteinas=8, carbohidratos=18)
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)
        data = {
            'nombre': 'Nombre Editado',
            'proteinas': 12,
            'carbohidratos': 22,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        receta.refresh_from_db()
        self.assertEqual(receta.nombre, 'Nombre Editado')
        self.assertTrue(response.context['exito'])

    def test_editar_receta_post_proteina_negativa(self):
        receta = Receta.objects.create(
            nombre="Original", proteinas=10, carbohidratos=20, familia=self.familia
        )
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)

        data = {
            'nombre': 'Actualizada',
            'proteinas': -10,  # inválido
            'carbohidratos': 25,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }

        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('proteinas', form.errors)

    def test_editar_receta_post_nombre_vacio(self):
        receta = Receta.objects.create(
            nombre="Original", proteinas=10, carbohidratos=20, familia=self.familia
        )
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)

        data = {
            'nombre': '',  # inválido
            'proteinas': 10,
            'carbohidratos': 20,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }

        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_editar_receta_post_sin_tipo_comida(self):
        receta = Receta.objects.create(
            nombre="Sin Tipo", proteinas=10, carbohidratos=10, familia=self.familia
        )
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)

        data = {
            'nombre': 'Revisión',
            'proteinas': 10,
            'carbohidratos': 10,
            'combinable': True,
            'tipo_comida': [],  # vacío
            'ingredientes': [self.ingrediente.id],
        }

        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('tipo_comida', form.errors)

    def test_editar_receta_post_valido_no_combinable(self):
        receta = Receta.objects.create(
            nombre="Combinable", proteinas=15, carbohidratos=20, combinable=True, familia=self.familia
        )
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)

        data = {
            'nombre': 'No Combinable',
            'proteinas': 12,
            'carbohidratos': 18,
            'combinable': False,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }

        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        receta.refresh_from_db()
        self.assertEqual(receta.nombre, 'No Combinable')
        self.assertFalse(receta.combinable)
        self.assertTrue(response.context['exito'])

    def test_editar_receta_post_nombre_con_acentos(self):
        receta = Receta.objects.create(
            nombre="Viejo Nombre", proteinas=10, carbohidratos=10, familia=self.familia
        )
        receta.tipo_comida.add(self.tipo)
        receta.ingredientes.add(self.ingrediente)

        data = {
            'nombre': 'Sopa de Ñame y Pimiento',
            'proteinas': 10,
            'carbohidratos': 10,
            'combinable': True,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }

        response = self.client.post(reverse('editar_receta', args=[receta.id]), data)
        self.assertEqual(response.status_code, 200)
        receta.refresh_from_db()
        self.assertEqual(receta.nombre, 'Sopa de Ñame y Pimiento')
