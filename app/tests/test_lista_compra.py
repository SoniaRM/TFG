from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.timezone import now
from datetime import timedelta
from app.models import Familia, Receta, ListaCompra, ListaCompraItem, Ingrediente, TipoComida, Calendario, Calendario_Receta
from app.views.lista_compra import generar_lista_compra

class ListaCompraViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.familia = Familia.objects.create(nombre="TestFamilia", administrador=self.user)
        self.familia.miembros.add(self.user)
        self.ingrediente = Ingrediente.objects.create(nombre="Zanahoria", familia=self.familia, frec=1)
        self.client.login(username='testuser', password='12345')
        self.start_date = now().date() - timedelta(days=now().date().weekday())
        self.lista = ListaCompra.objects.create(start_date=self.start_date, familia=self.familia)
        self.item = ListaCompraItem.objects.create(
            lista=self.lista,
            ingrediente=self.ingrediente,
            original=5,
            compra=3,
            despensa=2
        )

    def test_vista_lista_compra(self):
        response = self.client.get(reverse('lista_compra'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lista_compra.html')
        self.assertIn('ingredientes_por_comprar', response.context)
        self.assertIn('ingredientes_en_despensa', response.context)

    def test_mover_compra_despensa(self):
        response = self.client.post(reverse('mover_compra_despensa'), {
            'lista_id': self.lista.id,
            'item_id': self.item.id,
            'raciones': 1
        })
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 3)
        self.assertEqual(self.item.compra, 2)
    
    def test_mover_compra_despensa_supera_original(self):
        self.item.despensa = 4
        self.item.compra = 1
        self.item.save()
        response = self.client.post(reverse('mover_compra_despensa'), {
            'lista_id': self.lista.id,
            'item_id': self.item.id,
            'raciones': 2  # superaría original = 5
        })
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 5)
        self.assertEqual(self.item.compra, 0)


    def test_mover_despensa_compra(self):
        response = self.client.post(reverse('mover_despensa_compra'), {
            'lista_id': self.lista.id,
            'item_id': self.item.id,
            'raciones': 1
        })
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 1)
        self.assertEqual(self.item.compra, 4)
    
    def test_mover_despensa_compra_bajo_cero(self):
        self.item.despensa = 0
        self.item.compra = 5
        self.item.save()
        response = self.client.post(reverse('mover_despensa_compra'), {
            'lista_id': self.lista.id,
            'item_id': self.item.id,
            'raciones': 2
        })
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 0)
        self.assertEqual(self.item.compra, 5)


    def test_mover_compra_despensa_error_permiso(self):
        other_user = User.objects.create_user(username='otheruser', password='12345')
        other_familia = Familia.objects.create(nombre='Otra', administrador=other_user)
        other_ingrediente = Ingrediente.objects.create(nombre="Puerro", familia=other_familia, frec=1)
        other_lista = ListaCompra.objects.create(start_date=self.start_date, familia=other_familia)
        other_item = ListaCompraItem.objects.create(lista=other_lista, ingrediente=other_ingrediente, original=3, compra=3, despensa=0)
        response = self.client.post(reverse('mover_compra_despensa'), {
            'lista_id': other_lista.id,
            'item_id': other_item.id,
            'raciones': 1
        })
        self.assertEqual(response.status_code, 403)

    def test_lista_compra_datos(self):
        response = self.client.get(reverse('lista_compra_datos') + f'?start={self.start_date}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('por_comprar', response.json())
        self.assertIn('en_despensa', response.json())

    def test_lista_compra_datos_fecha_invalida(self):
        with self.assertRaises(ValueError):
            self.client.get(reverse('lista_compra_datos') + '?start=invalid-date')


    def test_generar_lista_compra_actualiza_items(self):
        TipoComida.objects.all().delete()
        # Crear receta con ingrediente
        tipo = TipoComida.objects.create(nombre="Almuerzo")
        receta = Receta.objects.create(
            nombre="Sopa", proteinas=10, carbohidratos=20, familia=self.familia
        )
        receta.tipo_comida.add(tipo)
        receta.ingredientes.add(self.ingrediente)

        # Crear calendario con receta asignada
        fecha = self.start_date
        calendario = Calendario.objects.create(fecha=fecha, familia=self.familia)
        Calendario_Receta.objects.create(calendario=calendario, receta=receta, tipo_comida=tipo)

        # Ejecutar función
        generar_lista_compra(self.start_date, self.familia)

        # Verificar actualización
        item = ListaCompraItem.objects.get(lista=self.lista, ingrediente=self.ingrediente)
        self.assertEqual(item.original, 1)
        self.assertEqual(item.despensa, 1)
        self.assertEqual(item.compra, 0)

    def test_finalizar_compra(self):
        response = self.client.post(reverse('finalizar_compra'), data={
            'items': [{'item_id': self.item.id, 'cantidad': '1'}],
            'start': self.start_date.isoformat()
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 3)
        self.assertEqual(self.item.compra, 2)

    def test_finalizar_compra_fecha_invalida(self):
        response = self.client.post(reverse('finalizar_compra'), data={
            'items': [{'item_id': self.item.id, 'cantidad': '2'}],
            'start': 'not-a-date'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Fecha inválida", response.json().get('error', ''))

    def test_resetear_lista_compra(self):
        self.item.despensa = 2
        self.item.compra = 3
        self.item.save()
        response = self.client.post(reverse('reset_lista_compra') + f'?start={self.start_date}')
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.despensa, 0)
        self.assertEqual(self.item.compra, 5)

    def test_exportar_lista_compra(self):
        response = self.client.get(reverse('exportar_lista_compra') + f'?start={self.start_date}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "application/pdf")
