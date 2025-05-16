from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from app.models import Familia, Calendario, SolicitudUniónFamilia

class ConfigurarObjetivoViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.familia = Familia.objects.create(nombre='TestFamilia', administrador=self.user)
        self.familia.miembros.add(self.user)
        self.client.login(username='testuser', password='12345')
        self.url = reverse('configurar_objetivo') 

    def test_get_configurar_objetivo_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTemplateUsed(response, 'configurar_objetivo.html')

    def test_post_configurar_objetivo_valido(self):
        hoy = timezone.now().date()
        data = {
            'objetivo_proteico': 100,
            'objetivo_carbohidratos': 200,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['exito'])

        calendario = Calendario.objects.get(fecha=hoy, familia=self.familia)
        self.assertEqual(calendario.objetivo_proteico, 100)
        self.assertEqual(calendario.objetivo_carbohidratos, 200)

