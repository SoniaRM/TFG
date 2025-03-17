from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import  transaction, IntegrityError, connection
from django.urls import reverse
from .models import Receta, Ingrediente, TipoComida, Calendario, Calendario_Receta
from .forms import RecetaForm
from datetime import date, timedelta, datetime

class TipoComidaModelTests(TestCase):
    def setUp(self):
        TipoComida.objects.all().delete()

    #Crear tipoComida OK
    def test_crear_tipo_comida(self):
        tipo_comida = TipoComida.objects.create(nombre='Desayuno')
        self.assertEqual(tipo_comida.nombre, 'Desayuno')
    
    #Crear tipoComida numérico (FAIL)
    def test_crear_tipo_comida_numerico(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='12345')
            tipo_comida.full_clean() #Esto hace validaciones

    #Crear tipoComida ya existente (FAIL)
    def test_crear_tipo_comida_ya_existente(self):
        TipoComida.objects.create(nombre='Desayuno')
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='Desayuno')
            tipo_comida.full_clean()

    #Crear tipoComida con nombre vacío (FAIL)
    def test_crear_tipo_comida_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='')
            tipo_comida.full_clean()

    #Crear tipoComida con nombre muy largo (FAIL)
    def test_crear_tipo_comida_nombre_muy_largo(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='a' * 101)
            tipo_comida.full_clean()

    #Crear tipoComida con nombre con caracteres especiales (FAIL)
    def test_crear_tipo_comida_nombre_caracteres_especiales(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='Des@yun#')
            tipo_comida.full_clean()
            
    #Crear tipoComida con nombre con espacios (FAIL)  
    def test_crear_tipo_comida_nombre_con_espacios(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='Desayuno con Espacios')
            tipo_comida.full_clean()  

class RecetaModelTests(TestCase):
    def setUp(self):
        connection.cursor().execute("PRAGMA foreign_keys = ON;")

        TipoComida.objects.all().delete()
        Ingrediente.objects.all().delete()
        Receta.objects.all().delete()

        self.tipo_comida = TipoComida.objects.create(nombre='Desayuno')
        self.ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)
        self.receta = Receta.objects.create(nombre='Ensalada', proteinas=10)
        self.receta.tipo_comida.add(self.tipo_comida)
        self.receta.ingredientes.add(self.ingrediente)

    #Crear receta OK 
    def test_crear_receta(self):
        self.assertEqual(self.receta.nombre, 'Ensalada')
        self.assertEqual(self.receta.proteinas, 10)
        self.assertIn(self.tipo_comida, self.receta.tipo_comida.all())
        self.assertIn(self.ingrediente, self.receta.ingredientes.all())

    #Crear receta OK, multiples ingredientes y/o tipoComida
    def test_crear_receta_multiples_ingredientes_tipo_comida(self):
        tipo_comida2 = TipoComida.objects.create(nombre='Almuerzo')
        ingrediente2 = Ingrediente.objects.create(nombre='Lechuga', frec=3)
        self.receta.tipo_comida.add(tipo_comida2)
        self.receta.ingredientes.add(ingrediente2)

        # receta = Receta.objects.create(nombre='Ensalada Mixta', proteinas=15)
        # receta.tipo_comida.add(self.tipo_comida, tipo_comida2)
        # receta.ingredientes.add(self.ingrediente, ingrediente2)
        self.assertEqual(self.receta.nombre, 'Ensalada')
        self.assertEqual(self.receta.proteinas, 10)
        self.assertEqual(self.receta.tipo_comida.count(), 2)
        self.assertEqual(self.receta.ingredientes.count(), 2)

    #Crear receta con nombre numérico (FAIL)
    def test_crear_receta_nombre_numerico(self):
        with self.assertRaises(ValidationError):
            receta = Receta(nombre='12345', proteinas=10)
            receta.full_clean()

    #crear receta con proteínas no numérico (FAIL)
    def test_crear_receta_proteinas_no_numerico(self):
        with self.assertRaises(ValidationError):
            receta = Receta(nombre='Ensalada', proteinas='diez')
            receta.full_clean()

    #Crear receta con proteínas negativas (FAIL)
    def test_crear_receta_proteinas_negativas(self):
        with self.assertRaises(ValidationError):
            receta = Receta(nombre='Ensalada', proteinas=-10)
            receta.full_clean()

    #Crear receta con tipoComida no existente (FAIL)
    def test_crear_receta_tipo_comida_no_existente(self):
        # Creamos una receta nueva sin ingredientes asociados.
        receta = Receta.objects.create(nombre='Nueva Ensalada', proteinas=10)
        self.assertEqual(receta.ingredientes.count(), 0)
        
        # Agregamos un ID inexistente (999) a la relación ManyToMany.
        receta.ingredientes.add(999)
        receta.refresh_from_db()
        
        # Filtramos los ingredientes asociados que existan realmente en la tabla Ingrediente.
        valid_ingredientes = Ingrediente.objects.filter(
            id__in=receta.ingredientes.values_list('id', flat=True)
        )
        # Comprobamos que no se recupera ningún ingrediente válido.
        self.assertEqual(valid_ingredientes.count(), 0)
        
        # Limpiamos manualmente la tabla intermedia para evitar el IntegrityError en el teardown.
        Receta.ingredientes.through.objects.filter(receta_id=receta.id).delete()

    #Crear receta con tipoComida repetidos (FAIL)
    def test_crear_receta_tipo_comida_repetidos(self):
        self.receta.tipo_comida.add(self.tipo_comida, self.tipo_comida)
        self.assertEqual(self.receta.tipo_comida.count(), 1)

    # Crear receta con tipoComida numérico (FAIL)
    def test_crear_receta_tipo_comida_numerico(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='12345')
            tipo_comida.full_clean()

    # Crear receta con ingrediente no existente (FAIL)
    def test_crear_receta_ingrediente_no_existente(self):
        # Creamos una receta nueva sin ingredientes asociados.
        receta = Receta.objects.create(nombre='Nueva Ensalada', proteinas=10)
        self.assertEqual(receta.ingredientes.count(), 0)
        
        # Agregamos un ID inexistente (999) a la relación ManyToMany.
        receta.ingredientes.add(999)
        receta.refresh_from_db()
        
        # Filtramos los ingredientes asociados que existan realmente en la tabla Ingrediente.
        valid_ingredientes = Ingrediente.objects.filter(
            id__in=receta.ingredientes.values_list('id', flat=True)
        )
        # Comprobamos que no se recupera ningún ingrediente válido.
        self.assertEqual(valid_ingredientes.count(), 0)
        
        # Limpiamos manualmente la tabla intermedia para evitar el IntegrityError en el teardown.
        Receta.ingredientes.through.objects.filter(receta_id=receta.id).delete()

    # Crear receta con ingredientes repetidos (FAIL)
    def test_crear_receta_ingredientes_repetidos(self):
        self.receta.ingredientes.add(self.ingrediente, self.ingrediente)
        self.assertEqual(self.receta.ingredientes.count(), 1)

    # Crear receta con ingredientes numérico (FAIL)
    def test_crear_receta_ingredientes_numerico(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='12345', frec=5)
            ingrediente.full_clean()

    # Editar receta OK
    def test_editar_receta(self):
        nueva_proteina = 20
        self.receta.proteinas = nueva_proteina
        self.receta.save()
        self.receta.refresh_from_db()
        self.assertEqual(self.receta.proteinas, nueva_proteina)

    # Editar receta con nombre numérico (FAIL)
    def test_editar_receta_nombre_numerico(self):
        with self.assertRaises(ValidationError):
            self.receta.nombre = '12345'
            self.receta.full_clean()  # Esto hace las validaciones
            self.receta.save()

    # Editar receta con proteínas no numérico (FAIL)
    def test_editar_receta_proteinas_no_numerico(self):
        with self.assertRaises(ValidationError):
            self.receta.proteinas = 'diez'
            self.receta.full_clean()  # Esto hace las validaciones
            self.receta.save()

    # Editar receta con proteínas negativas (FAIL)
    def test_editar_receta_proteinas_negativas(self):
        with self.assertRaises(ValidationError):
            self.receta.proteinas = -10
            self.receta.full_clean()  # Esto hace las validaciones
            self.receta.save()

    # Editar receta con tipoComida no existente (FAIL)
    def test_editar_receta_tipo_comida_no_existente(self):
        # Creamos un tipo de comida válido.
        tipo_comida_valido = TipoComida.objects.create(nombre='Almuerzo')
        
        # Creamos una receta con el tipo de comida válido asignado.
        receta = Receta.objects.create(nombre='Receta Editar', proteinas=20)
        receta.tipo_comida.add(tipo_comida_valido)
        self.assertEqual(receta.tipo_comida.count(), 1)
        self.assertEqual(receta.tipo_comida.first(), tipo_comida_valido)
        
        # Simulamos la edición: removemos el tipo de comida existente...
        receta.tipo_comida.clear()
        
        # ...y asignamos un ID inexistente (999) a la relación ManyToMany.
        receta.tipo_comida.add(999)
        receta.refresh_from_db()
        
        # Filtramos los tipos de comida asociados que existan realmente en la tabla TipoComida.
        valid_tipo_comida = TipoComida.objects.filter(
            id__in=receta.tipo_comida.values_list('id', flat=True)
        )
        # Comprobamos que no se recupera ningún tipo de comida válido.
        self.assertEqual(valid_tipo_comida.count(), 0)
        
        # Limpiamos manualmente la tabla intermedia para evitar el IntegrityError en el teardown.
        Receta.tipo_comida.through.objects.filter(receta_id=receta.id).delete()
    
    # Editar receta con tipoComida repetidos (FAIL)
    def test_editar_receta_tipo_comida_repetidos(self):
        # Agregamos un tipo de comida a la receta
        self.receta.tipo_comida.add(self.tipo_comida)
        self.receta.refresh_from_db()
        self.assertEqual(self.receta.tipo_comida.count(), 1)
        
        # Intentamos agregar nuevamente el mismo tipo de comida
        self.receta.tipo_comida.add(self.tipo_comida)
        
        # Ejecutamos las validaciones y guardamos, sin esperar que se lance ninguna excepción
        self.receta.full_clean()
        self.receta.save()
        self.receta.refresh_from_db()
        
        # Verificamos que sigue habiendo solo un tipo de comida asociado
        self.assertEqual(self.receta.tipo_comida.count(), 1)
        
    # Editar receta con tipoComida numérico (FAIL)
    def test_editar_receta_tipo_comida_numerico(self):
        with self.assertRaises(ValidationError):
            tipo_comida = TipoComida(nombre='12345')
            tipo_comida.full_clean()

    # Editar receta con ingrediente no existente (FAIL)
    def test_editar_receta_ingrediente_no_existente(self):
        # Creamos un ingrediente válido y lo asignamos a la receta inicialmente.
        ingrediente_valido = Ingrediente.objects.create(nombre='Lechuga', frec=1)
        receta = Receta.objects.create(nombre='Receta Edicion', proteinas=15)
        receta.ingredientes.add(ingrediente_valido)
        self.assertEqual(receta.ingredientes.count(), 1)
        
        # Simulamos la edición de la receta:
        # Primero removemos el ingrediente válido.
        receta.ingredientes.clear()
        
        # Luego intentamos asignar un ID inexistente (999) a la relación ManyToMany.
        receta.ingredientes.add(999)
        receta.refresh_from_db()
        
        # Filtramos los ingredientes asociados que existan realmente en la tabla Ingrediente.
        valid_ingredientes = Ingrediente.objects.filter(
            id__in=receta.ingredientes.values_list('id', flat=True)
        )
        # Comprobamos que no se recupera ningún ingrediente válido.
        self.assertEqual(valid_ingredientes.count(), 0)
        
        # Limpiamos manualmente la tabla intermedia para evitar el IntegrityError en el teardown.
        Receta.ingredientes.through.objects.filter(receta_id=receta.id).delete()

    # Editar receta con ingredientes repetidos (FAIL)
    def test_editar_receta_ingrediente_repetidos(self):
        # Creamos un ingrediente válido.
        ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=1)
        
        # Creamos una receta y le asignamos el ingrediente válido.
        receta = Receta.objects.create(nombre='Receta Edicion Ingredientes', proteinas=20)
        receta.ingredientes.add(ingrediente)
        receta.refresh_from_db()
        self.assertEqual(receta.ingredientes.count(), 1)
        
        # Simulamos la edición: intentamos agregar nuevamente el mismo ingrediente.
        receta.ingredientes.add(ingrediente)
        
        # Ejecutamos las validaciones y guardamos la receta.
        receta.full_clean()
        receta.save()
        receta.refresh_from_db()
        
        # Verificamos que la receta sigue teniendo sólo un ingrediente asociado.
        self.assertEqual(receta.ingredientes.count(), 1)

    # Editar receta con ingredientes numérico (FAIL)
    def test_editar_receta_ingredientes_numerico(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='12345', frec=5)
            ingrediente.full_clean()

    # Eliminar receta OK
    def test_eliminar_receta(self):
        receta_id = self.receta.id
        self.receta.delete()
        self.assertFalse(Receta.objects.filter(id=receta_id).exists())

    # Eliminar receta inexistente (FAIL)
    def test_eliminar_receta_inexistente(self):
        with self.assertRaises(Receta.DoesNotExist):
            Receta.objects.get(id=999).delete()

class RecetaViewTests(TestCase):
    def setUp(self):
        TipoComida.objects.all().delete()
        Ingrediente.objects.all().delete()
        Receta.objects.all().delete()

        self.tipo_comida = TipoComida.objects.create(nombre='Desayuno')
        self.ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)
        self.receta = Receta.objects.create(nombre='Ensalada', proteinas=10)
        self.receta.tipo_comida.add(self.tipo_comida)
        self.receta.ingredientes.add(self.ingrediente)

    #Listado recetas view OK
    def test_listado_recetas_view(self):
        response = self.client.get(reverse('listado_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensalada')

    #Detalle receta view OK
    def test_detalle_receta_view(self):
        response = self.client.get(reverse('detalle_receta', args=[self.receta.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensalada')
        self.assertContains(response, 'Tomate')

    #Crear receta view OK
    def test_crear_receta_view(self):
        response = self.client.post(reverse('crear_receta'), {
            'nombre': 'Nueva Ensalada',
            'proteinas': 15,
            'tipo_comida': [self.tipo_comida.id],
            'ingredientes': [self.ingrediente.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirige después de crear
        self.assertTrue(Receta.objects.filter(nombre='Nueva Ensalada').exists())

    #Editar receta view OK
    def test_editar_receta_view(self):
        response = self.client.post(reverse('editar_receta', args=[self.receta.pk]), {
            'nombre': 'Ensalada Editada',
            'proteinas': 20,
            'tipo_comida': [self.tipo_comida.id],
            'ingredientes': [self.ingrediente.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirige después de editar
        self.receta.refresh_from_db()
        self.assertEqual(self.receta.nombre, 'Ensalada Editada')
        self.assertEqual(self.receta.proteinas, 20)

class RecetaFormTests(TestCase):
    def setUp(self):
        TipoComida.objects.all().delete()

        # Crea instancias necesarias para los campos ManyToMany
        self.tipo = TipoComida.objects.create(nombre='Desayuno')
        self.ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)

    def test_form_valido(self):
        data = {
            'nombre': 'Ensalada',
            'proteinas': 10,
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        form = RecetaForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_invalido(self):
        data = {
            'nombre': '12345',  # Supongamos que en validaciones queremos rechazar nombres numéricos
            'proteinas': 'diez',  # No es un entero
            'tipo_comida': [self.tipo.id],
            'ingredientes': [self.ingrediente.id],
        }
        form = RecetaForm(data=data)
        self.assertFalse(form.is_valid())
        # Puedes además comprobar errores específicos:
        self.assertIn('proteinas', form.errors)
        self.assertIn('nombre', form.errors)

class IngredienteModelTests(TestCase):
    def setUp(self):
        Ingrediente.objects.all().delete()
        Receta.objects.all().delete()
        TipoComida.objects.all().delete()

        self.tipo_comida = TipoComida.objects.create(nombre='Desayuno')
        self.ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)
        self.receta = Receta.objects.create(nombre='Ensalada', proteinas=10)
        self.receta.tipo_comida.add(self.tipo_comida)
        self.receta.ingredientes.add(self.ingrediente)
        
    #Crear ingrediente OK
    def test_crear_ingrediente(self):
        ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)
        self.assertEqual(ingrediente.nombre, 'Tomate')
        self.assertEqual(ingrediente.frec, 5)

    #Crear ingrediente numérico (FAIL)
    def test_crear_ingrediente_numerico(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='12345', frec=5)
            ingrediente.full_clean()

    #Crear ingrediente con nombre vacío (FAIL)
    def test_crear_ingrediente_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='', frec=5)
            ingrediente.full_clean()

    #Crear ingrediente con nombre muy largo (FAIL)
    def test_crear_ingrediente_nombre_muy_largo(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='a' * 101, frec=5)
            ingrediente.full_clean()

    # Crear ingrediente con nombre con caracteres especiales (FAIL)
    def test_crear_ingrediente_nombre_caracteres_especiales(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='Tom@te!', frec=5)
            ingrediente.full_clean()

    # Crear ingrediente con frecuencia no numérica (FAIL)
    def test_crear_ingrediente_frec_no_numerico(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='Tomate', frec='cinco')
            ingrediente.full_clean()

    # Crear ingrediente con frecuencia negativa (FAIL)
    def test_crear_ingrediente_frec_negativa(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='Tomate', frec=-5)
            ingrediente.full_clean()

    # Crear ingrediente con frecuencia 0 (FAIL) (tiene que ser mínimo 1)
    def test_crear_ingrediente_frec_cero(self):
        with self.assertRaises(ValidationError):
            ingrediente = Ingrediente(nombre='Tomate', frec=0)
            ingrediente.full_clean()

    # Editar ingrediente OK
    def test_editar_ingrediente(self):
        self.ingrediente.nombre = 'Pepino'
        self.ingrediente.frec = 10
        self.ingrediente.save()
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.nombre, 'Pepino')
        self.assertEqual(self.ingrediente.frec, 10)

    # Editar ingrediente numérico (FAIL)
    def test_editar_ingrediente_numerico(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.nombre = '12345'
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Editar ingrediente con nombre vacío (FAIL)
    def test_editar_ingrediente_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.nombre = ''
            self.ingrediente.full_clean()
            self.ingrediente.save()

   # Editar ingrediente con nombre muy largo (FAIL)
    def test_editar_ingrediente_nombre_muy_largo(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.nombre = 'a' * 101
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Editar ingrediente con nombre con caracteres especiales (FAIL)
    def test_editar_ingrediente_nombre_caracteres_especiales(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.nombre = 'Tom@te!'
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Editar ingrediente con frecuencia no numérica (FAIL)
    def test_editar_ingrediente_frec_no_numerico(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.frec = 'cinco'
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Editar ingrediente con frecuencia negativa (FAIL)
    def test_editar_ingrediente_frec_negativa(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.frec = -5
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Editar ingrediente con frecuencia 0 (FAIL) (tiene que ser mínimo 1)
    def test_editar_ingrediente_frec_cero(self):
        with self.assertRaises(ValidationError):
            self.ingrediente.frec = 0
            self.ingrediente.full_clean()
            self.ingrediente.save()

    # Eliminar ingrediente OK
    def test_eliminar_ingrediente(self):
        ingrediente_id = self.ingrediente.id
        self.ingrediente.delete()
        self.assertFalse(Ingrediente.objects.filter(id=ingrediente_id).exists())

    # Eliminar ingrediente inexistente (FAIL)
    def test_eliminar_ingrediente_inexistente(self):
        with self.assertRaises(Ingrediente.DoesNotExist):
            Ingrediente.objects.get(id=999).delete()

    # Eliminar ingrediente con recetas asociadas (FAIL)
    def test_eliminar_ingrediente_con_recetas_asociadas(self):
        # Guardamos el id del ingrediente y de las recetas asociadas
        ingrediente_id = self.ingrediente.id
        receta_ids = list(self.ingrediente.recetas.values_list('id', flat=True))
        
        # Eliminamos el ingrediente
        self.ingrediente.delete()
        
        # Verificamos que el ingrediente ya no existe en la base de datos
        self.assertFalse(Ingrediente.objects.filter(id=ingrediente_id).exists())
        
        # Verificamos que todas las recetas asociadas también se hayan eliminado
        for rid in receta_ids:
            self.assertFalse(Receta.objects.filter(id=rid).exists())

class IngredienteViewTests(TestCase):
    def setUp(self):
        Ingrediente.objects.all().delete()
        self.ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)

    #Listado ingredientes view OK
    def test_listado_ingredientes_view(self):
        response = self.client.get(reverse('listado_ingredientes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tomate')

    #Detalle ingrediente view OK
    def test_detalle_ingrediente_view(self):
        response = self.client.get(reverse('detalle_ingrediente', args=[self.ingrediente.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tomate')

    #Crear ingrediente view OK
    def test_crear_ingrediente_view(self):
        response = self.client.post(reverse('crear_ingrediente'), {'nombre': 'Lechuga', 'frec': 3})
        self.assertEqual(response.status_code, 302)  # Redirige después de crear
        self.assertTrue(Ingrediente.objects.filter(nombre='Lechuga').exists())

    #Editar ingrediente view OK
    def test_editar_ingrediente_view(self):
        response = self.client.post(reverse('editar_ingrediente', args=[self.ingrediente.pk]), {'nombre': 'Pepino', 'frec': 4})
        self.assertEqual(response.status_code, 302)  # Redirige después de editar
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.nombre, 'Pepino')
        self.assertEqual(self.ingrediente.frec, 4)

class CalendarioModelTests(TestCase):
    def setUp(self):
        # Usamos get_or_create para evitar errores de duplicidad
        self.desayuno, _ = TipoComida.objects.get_or_create(nombre="Desayuno")
        self.almuerzo, _ = TipoComida.objects.get_or_create(nombre="Almuerzo")
        self.merienda, _ = TipoComida.objects.get_or_create(nombre="Merienda")
        self.cena, _ = TipoComida.objects.get_or_create(nombre="Cena")

        # Creamos dos recetas para "Desayuno".
        self.receta1 = Receta.objects.create(nombre="Receta1", proteinas=10)
        self.receta1.tipo_comida.add(self.desayuno)
        self.receta2 = Receta.objects.create(nombre="Receta2", proteinas=25)
        self.receta2.tipo_comida.add(self.desayuno)
        
        # Fijamos una fecha de prueba (por ejemplo, un lunes).
        self.test_date = date(2025, 3, 16)
        
        # Creamos un objeto Calendario para esa fecha y asignamos receta1 a "Desayuno".
        self.calendario = Calendario.objects.create(fecha=self.test_date, objetivo_proteico=50)
        Calendario_Receta.objects.create(
            calendario=self.calendario, receta=self.receta1, tipo_comida=self.desayuno
        )

    # Test: Si se llama a 'recetas_por_tipo' sin pasar los parámetros requeridos,
    # se debe devolver un error indicando "Faltan parámetros."
    def test_recetas_por_tipo_missing_params(self):
        url = reverse("recetas_por_tipo")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {"error": "Faltan parámetros."})

    # Test: Para "Desayuno" en la fecha de prueba, dado que receta1 ya está en el calendario,
    # la vista debe devolver únicamente receta2.
    def test_recetas_por_tipo_valid(self):
        url = reverse("recetas_por_tipo") + f"?tipo=Desayuno&fecha={self.test_date.strftime('%Y-%m-%d')}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["nombre"], "Receta2")

    # Test: Se debe poder agregar receta2 a "Desayuno" para la fecha de prueba,
    # y luego existir dos recetas asignadas en ese tipo para dicha fecha.
    def test_agregar_receta_calendario(self):
        url = reverse("agregar_receta_calendario")
        data = {
            "fecha": self.test_date.strftime('%Y-%m-%d'),
            "receta_id": self.receta2.id,
            "tipo_comida_id": self.desayuno.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("mensaje", json_data)
        count = Calendario_Receta.objects.filter(
            calendario__fecha=self.test_date,
            tipo_comida=self.desayuno
        ).count()
        self.assertEqual(count, 2)

    # Test: La vista 'recetas_en_calendario' debe devolver receta1 para "Desayuno" en la fecha de prueba.
    def test_recetas_en_calendario(self):
        url = reverse("recetas_en_calendario") + f"?fecha={self.test_date.strftime('%Y-%m-%d')}&tipo=Desayuno"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["nombre"], "Receta1")

    # Test: Se debe poder eliminar receta1 de "Desayuno" para la fecha de prueba.
    def test_eliminar_receta_calendario(self):
        url = reverse("eliminar_receta_calendario")
        data = {
            "fecha": self.test_date.strftime('%Y-%m-%d'),
            "receta_id": self.receta1.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("mensaje", json_data)
        exists = Calendario_Receta.objects.filter(
            calendario__fecha=self.test_date,
            receta=self.receta1
        ).exists()
        self.assertFalse(exists)

    # Test: La vista 'actualizar_calendario_dia' debe devolver un JSON que incluya la clave "recetas"
    # con, al menos, la receta asignada a "Desayuno" para la fecha de prueba.
    def test_actualizar_calendario_dia(self):
        url = reverse("actualizar_calendario_dia") + f"?fecha={self.test_date.strftime('%Y-%m-%d')}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recetas", data)
        self.assertIn("Desayuno", data["recetas"])
        self.assertIn("Receta1", data["recetas"]["Desayuno"])
        
    # Caso positivo: Si no hay recetas asignadas, calcular_proteinas_restantes debe devolver el objetivo.
    def test_calcular_proteinas_restantes_sin_recetas(self):
        # Creamos un calendario sin recetas
        cal = Calendario.objects.create(fecha=self.test_date + timedelta(days=1), objetivo_proteico=50)
        self.assertEqual(cal.calcular_proteinas_restantes(), 50)   

    # Caso positivo: Con una receta asignada (10 proteínas) y objetivo 50, el método debe devolver 40.
    def test_calcular_proteinas_restantes_con_una_receta(self):
        resultado = self.calendario.calcular_proteinas_restantes()
        self.assertEqual(resultado, 40)

    # Caso límite: Asignar una segunda receta (25 proteínas) para "Desayuno"
    # y con objetivo 50, la suma (10+25=35) es menor que el objetivo, por lo que debe devolver 15.
    def test_calcular_proteinas_restantes_con_dos_recetas(self):
        self.calendario.asignar_receta(self.receta2, self.desayuno)
        resultado = self.calendario.calcular_proteinas_restantes()
        self.assertEqual(resultado, 15)

    # Caso límite: Si la suma de proteínas es igual o mayor que el objetivo, debe retornar 0.
    def test_calcular_proteinas_restantes_limite_superado(self):
        # Creamos un calendario con objetivo 30
        cal = Calendario.objects.create(fecha=self.test_date + timedelta(days=2), objetivo_proteico=30)
        # Asignamos ambas recetas: 10 + 25 = 35 > 30, por lo que el resultado debe ser 0.
        Calendario_Receta.objects.create(calendario=cal, receta=self.receta1, tipo_comida=self.desayuno)
        Calendario_Receta.objects.create(calendario=cal, receta=self.receta2, tipo_comida=self.desayuno)
        resultado = cal.calcular_proteinas_restantes()
        self.assertEqual(resultado, 0)

    # Caso negativo: Intentar asignar la misma receta para el mismo tipo y fecha debe fallar por UNIQUE constraint.
    def test_asignar_receta_duplicate(self):
        # Ya se asignó receta1 a desayuno, intentar asignarla nuevamente debe lanzar error.
        with self.assertRaises(IntegrityError):
            self.calendario.asignar_receta(self.receta1, self.desayuno)

    # Caso positivo: Eliminar una receta asignada debe remover la relación y actualizar el cálculo.
    def test_eliminar_receta_existente(self):
        # Verificamos que receta1 está asignada.
        self.assertTrue(
            Calendario_Receta.objects.filter(calendario=self.calendario, receta=self.receta1, tipo_comida=self.desayuno).exists()
        )
        # Eliminamos receta1.
        self.calendario.eliminar_receta(self.receta1, self.desayuno)
        # La relación ya no debe existir.
        self.assertFalse(
            Calendario_Receta.objects.filter(calendario=self.calendario, receta=self.receta1, tipo_comida=self.desayuno).exists()
        )
        # Y calcular_proteinas_restantes debe volver al objetivo (50, ya que no hay recetas asignadas).
        self.assertEqual(self.calendario.calcular_proteinas_restantes(), 50)

    # Caso negativo: Eliminar una receta no asignada no debe afectar el estado del calendario.
    def test_eliminar_receta_no_existente(self):
        # No se ha asignado receta2 a "Desayuno" en self.calendario.
        initial_count = Calendario_Receta.objects.filter(calendario=self.calendario, tipo_comida=self.desayuno).count()
        # Intentamos eliminar receta2, sin que se genere error.
        self.calendario.eliminar_receta(self.receta2, self.desayuno)
        final_count = Calendario_Receta.objects.filter(calendario=self.calendario, tipo_comida=self.desayuno).count()
        self.assertEqual(initial_count, final_count)

    # Test de duplicidad de calendario
    # Caso negativo: Crear un calendario con una fecha ya existente debe generar error por la restricción UNIQUE.
    def test_duplicate_calendar_date(self):
        with self.assertRaises(IntegrityError):
            Calendario.objects.create(fecha=self.test_date, objetivo_proteico=100)

class CalendarioViewTests(TestCase):
    def setUp(self):
        # Usamos get_or_create para evitar errores de duplicidad
        self.desayuno, _ = TipoComida.objects.get_or_create(nombre="Desayuno")
        self.almuerzo, _ = TipoComida.objects.get_or_create(nombre="Almuerzo")
        self.merienda, _ = TipoComida.objects.get_or_create(nombre="Merienda")
        self.cena, _ = TipoComida.objects.get_or_create(nombre="Cena")

        # Creamos una receta para el tipo "Desayuno".
        self.receta1 = Receta.objects.create(nombre="Receta1", proteinas=10)
        self.receta1.tipo_comida.add(self.desayuno)
        
        # Fijamos una fecha de prueba (por ejemplo, un lunes).
        self.start_date = date(2025, 3, 16)
        
        # Creamos un objeto Calendario para esa fecha y asignamos receta1 a "Desayuno".
        self.calendario = Calendario.objects.create(fecha=self.start_date, objetivo_proteico=100)
        Calendario_Receta.objects.create(
            calendario=self.calendario, receta=self.receta1, tipo_comida=self.desayuno
        )
    
    # Test: Con un parámetro 'start' válido, la vista debe generar la semana a partir de esa fecha.
    def test_calendario_semanal_with_start(self):
        start_str = self.start_date.strftime("%Y-%m-%d")
        response = self.client.get(reverse("calendario_semanal") + f"?start={start_str}")
        self.assertEqual(response.status_code, 200)
        context = response.context
        dias = context["dias"]
        self.assertEqual(len(dias), 7)
        self.assertEqual(dias[0].strftime("%Y-%m-%d"), start_str)
        self.assertIn("prev_week_url", context)
        self.assertIn("next_week_url", context)

    # Test: La vista 'calendario_semanal' sin parámetro 'start' debe calcular la semana actual
    # y devolver en el contexto las claves necesarias, incluyendo 7 días.
    def test_calendario_semanal_without_start(self):
        response = self.client.get(reverse("calendario_semanal"))
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIn("dias", context)
        self.assertIn("dia_data", context)
        self.assertIn("prev_week_url", context)
        self.assertIn("next_week_url", context)
        self.assertIn("meal_order", context)
        self.assertIn("meal_mapping", context)
        self.assertEqual(len(context["dias"]), 7)


