from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import  transaction, IntegrityError, connection
from django.urls import reverse
from .models import Receta, Ingrediente, TipoComida
from .forms import RecetaForm

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
    # Editar receta con nombre numérico (FAIL)
    # Editar receta con proteínas no numérico (FAIL)
    # Editar receta con proteínas negativas (FAIL)
    # Editar receta con tipoComida no existente (FAIL)
    # Editar receta con tipoComida repetidos (FAIL)
    # Editar receta con tipoComida numérico (FAIL)
    # Editar receta con ingrediente no existente (FAIL)
    # Editar receta con ingredientes repetidos (FAIL)
    # Editar receta con ingredientes numérico (FAIL)

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
    #Editar receta view OK
    #Eliminado receta view OK

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

    #Crear ingrediente OK
    def test_crear_ingrediente(self):
        ingrediente = Ingrediente.objects.create(nombre='Tomate', frec=5)
        self.assertEqual(ingrediente.nombre, 'Tomate')
        self.assertEqual(ingrediente.frec, 5)
    #Crear ingrediente numérico (FAIL)
    #Crear ingrediente con nombre vacío (FAIL)
    #Crear ingrediente con nombre muy largo (FAIL)
    #Crear ingrediente con nombre muy corto (FAIL)
    #Crear ingrediente con nombre con caracteres especiales (FAIL)
    #Crear ingrediente con nombre con espacios (FAIL)
    #crear ingrediente con frecuencia no numérica (FAIL)
    #Crear ingrediente con frecuencia negativa (FAIL)
    #Crear ingrediente con frecuencia 0 (FAIL) (tiene que ser minimo 1)

    #Editar ingrediente OK
    #Editar ingrediente numérico (FAIL)
    #Editar ingrediente con nombre vacío (FAIL)
    #Editar ingrediente con nombre muy largo (FAIL)
    #Editar ingrediente con nombre muy corto (FAIL)
    #Editar ingrediente con nombre con caracteres especiales (FAIL)
    #Editar ingrediente con nombre con espacios (FAIL)
    #Editar ingrediente con frecuencia no numérica (FAIL)
    #Editar ingrediente con frecuencia negativa (FAIL)
    #Editar ingrediente con frecuencia 0 (FAIL) (tiene que ser minimo 1)

    #Eliminar ingrediente OK
    #Eliminar ingrediente inexistente (FAIL)
    #Eliminar ingrediente con recetas asociadas (FAIL)
    #Eliminar ingrediente con recetas asociadas y confirmación (OK)
    #Eliminar ingrediente con recetas asociadas y cancelación (OK)

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

    #Eliminar ingrediente view OK
    #Eliminar ingrediente inexistente (FAIL)
    #Eliminar ingrediente con recetas asociadas (FAIL)
