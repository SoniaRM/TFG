from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.models import Familia, Calendario, TipoComida, Receta, Calendario_Receta
from datetime import date, timedelta

class CalendarioViewsTest(TestCase):

    def setUp(self):
        TipoComida.objects.all().delete()
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.familia = Familia.objects.create(nombre='TestFamilia', administrador=self.user)
        self.familia.miembros.add(self.user)
        self.client.login(username='testuser', password='12345')
        self.tipo_comida = TipoComida.objects.create(nombre='Almuerzo')
        self.fecha = date.today()
        self.calendario = Calendario.objects.create(fecha=self.fecha, familia=self.familia,
                                                    objetivo_proteico=100, objetivo_carbohidratos=200)

    def test_calendario_semanal_render_default(self):
        response = self.client.get(reverse('calendario_semanal'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendario/semanal.html')
        self.assertIn('dias', response.context)
        self.assertIn('dia_data', response.context)
        self.assertEqual(len(response.context['dias']), 7)
    
    def test_calendario_semanal_con_parametro_valido(self):
        lunes = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        response = self.client.get(reverse('calendario_semanal') + f'?start={lunes}')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendario/semanal.html')
        self.assertEqual(len(response.context['dias']), 7)
    
    def test_calendario_semanal_con_parametro_invalido(self):
        response = self.client.get(reverse('calendario_semanal') + '?start=fecha-invalida')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendario/semanal.html')
        self.assertEqual(len(response.context['dias']), 7)  

    def test_calendario_semanal_view(self):
        response = self.client.get(reverse('calendario_semanal'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendario/semanal.html')

    def test_recetas_por_tipo_sin_parametros(self):
        response = self.client.get(reverse('recetas_por_tipo'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_recetas_por_tipo_sin_recetas_disponibles(self):
        fecha = date.today().isoformat()
        tipo_nombre = self.tipo_comida.nombre  
        response = self.client.get(reverse('recetas_por_tipo'), {
            'tipo': tipo_nombre,
            'fecha': fecha
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_agregar_receta_metodo_get_no_permitido(self):
        response = self.client.get(reverse('agregar_receta_calendario'))
        self.assertEqual(response.status_code, 405)
        self.assertIn('error', response.json())

    def test_agregar_receta_post_faltan_datos(self):
        response = self.client.post(reverse('agregar_receta_calendario'), {})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    def test_agregar_receta_duplicada(self):
        receta = Receta.objects.create(
            nombre="Gazpacho",
            familia=self.familia,
            proteinas=10,
            carbohidratos=20,
            combinable=True
        )
        receta.tipo_comida.add(self.tipo_comida)

        calendario = self.calendario 

        Calendario_Receta.objects.create(
            calendario=calendario,
            receta=receta,
            tipo_comida=self.tipo_comida
        )

        data = {
            "fecha": self.fecha.isoformat(),
            "receta_id": receta.id,
            "tipo_comida_id": self.tipo_comida.id
        }

        response = self.client.post(reverse('agregar_receta_calendario'), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_recetas_en_calendario_sin_calendario(self):
        response = self.client.get(reverse('recetas_en_calendario'), {
            "fecha": "2099-01-01",
            "tipo": self.tipo_comida.nombre
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_recetas_en_calendario_sin_recetas(self):
        response = self.client.get(reverse('recetas_en_calendario'), {
            "fecha": self.fecha.isoformat(),
            "tipo": self.tipo_comida.nombre
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_recetas_en_calendario_con_receta(self):
        receta = Receta.objects.create(
            nombre="Tortilla",
            familia=self.familia,
            proteinas=15,
            carbohidratos=10,
            combinable=True
        )
        receta.tipo_comida.add(self.tipo_comida)

        Calendario_Receta.objects.create(
            calendario=self.calendario,
            receta=receta,
            tipo_comida=self.tipo_comida
        )

        response = self.client.get(reverse('recetas_en_calendario'), {
            "fecha": self.fecha.isoformat(),
            "tipo": self.tipo_comida.nombre
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["nombre"], "Tortilla")

    def test_eliminar_receta_calendario_correctamente(self):
        receta = Receta.objects.create(
            nombre="Sopa",
            familia=self.familia,
            proteinas=10,
            carbohidratos=20,
            combinable=False
        )
        receta.tipo_comida.add(self.tipo_comida)

        cr = Calendario_Receta.objects.create(
            calendario=self.calendario,
            receta=receta,
            tipo_comida=self.tipo_comida
        )

        response = self.client.post(reverse('eliminar_receta_calendario'), {
            "fecha": self.fecha.isoformat(),
            "receta_id": receta.id,
            "tipo_comida": self.tipo_comida.nombre
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mensaje"], "Receta eliminada correctamente.")
        self.assertFalse(Calendario_Receta.objects.filter(id=cr.id).exists())

    def test_eliminar_receta_calendario_no_existente(self):
        response = self.client.post(reverse('eliminar_receta_calendario'), {
            "fecha": self.fecha.isoformat(),
            "receta_id": 999, 
            "tipo_comida": self.tipo_comida.nombre
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_eliminar_receta_calendario_metodo_no_permitido(self):
        response = self.client.get(reverse('eliminar_receta_calendario'))
        self.assertEqual(response.status_code, 405)
        self.assertIn("error", response.json())

    def test_actualizar_calendario_dia_view(self):
        response = self.client.get(reverse('actualizar_calendario_dia') + f'?fecha={self.fecha}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('objetivo_proteico', response.json())
        self.assertIn('proteinas_consumidas', response.json())

    def test_actualizar_calendario_dia_con_receta(self):
        receta = Receta.objects.create(
            nombre="Ensalada",
            familia=self.familia,
            proteinas=10,
            carbohidratos=5,
            combinable=True
        )
        receta.tipo_comida.add(self.tipo_comida)

        Calendario_Receta.objects.create(
            calendario=self.calendario,
            receta=receta,
            tipo_comida=self.tipo_comida
        )

        response = self.client.get(reverse('actualizar_calendario_dia'), {
            "fecha": self.fecha.isoformat()
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(self.tipo_comida.nombre, data["recetas"])
        self.assertIn("Ensalada", data["recetas"][self.tipo_comida.nombre])
        self.assertEqual(data["proteinas_consumidas"], 10)
        self.assertEqual(data["carbohidratos_consumidos"], 5)

    def test_actualizar_calendario_dia_sin_calendario(self):
        otra_fecha = self.fecha + timedelta(days=10)
        response = self.client.get(reverse('actualizar_calendario_dia'), {
            "fecha": otra_fecha.isoformat()
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recetas"], {})

    def test_actualizar_calendario_dia_sin_fecha(self):
        response = self.client.get(reverse('actualizar_calendario_dia'))
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_datos_dia_view(self):
        response = self.client.get(reverse('datos_dia', args=[self.fecha.isoformat()]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('objetivo_proteico', response.json())
        self.assertIn('proteinas_consumidas', response.json())

    def test_exportar_semana_pdf(self):
        response = self.client.get(reverse('exportar_semana') + f'?start={self.fecha}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "application/pdf")
