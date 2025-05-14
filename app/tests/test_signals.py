from django.test import TestCase
from django.contrib.auth.models import User
from django.core.management import call_command
from django.apps import apps
from app.models import TipoComida

class SignalsTestCase(TestCase):

    def test_crear_tipos_comida_post_migrate(self):
        # Asegura que la tabla esté vacía antes del test
        TipoComida.objects.all().delete()
        
        # Ejecuta explícitamente la señal post_migrate
        app_config = apps.get_app_config('app')
        call_command('migrate', app_config.label, verbosity=0)

        tipos_esperados = ["Desayuno", "Almuerzo", "Merienda", "Cena"]
        tipos_creados = TipoComida.objects.values_list('nombre', flat=True)

        # Verifica que todos los tipos esperados fueron creados
        for tipo in tipos_esperados:
            self.assertIn(tipo, tipos_creados)

        # Verifica que no haya tipos adicionales
        self.assertEqual(len(tipos_creados), len(tipos_esperados))
