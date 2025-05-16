from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command
from django.apps import apps
from app.models import TipoComida

class SignalsTestCase(TestCase):

    def test_crear_tipos_comida_post_migrate(self):
        TipoComida.objects.all().delete()
        
        app_config = apps.get_app_config('app')
        call_command('migrate', app_config.label, verbosity=0)

        tipos_esperados = ["Desayuno", "Almuerzo", "Merienda", "Cena"]
        tipos_creados = TipoComida.objects.values_list('nombre', flat=True)

        for tipo in tipos_esperados:
            self.assertIn(tipo, tipos_creados)

        self.assertEqual(len(tipos_creados), len(tipos_esperados))
