# app/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
import uuid

from app.models import (
    TipoComida, Familia, Ingrediente, Receta,
    Calendario, Calendario_Receta,
    ListaCompra, ListaCompraItem, SolicitudUniónFamilia
)


def random_letters(length=4):
    """Genera una cadena aleatoria de letras a-z sin dígitos."""
    letters = [c for c in uuid.uuid4().hex if c.isalpha()]
    if len(letters) < length:
        return 'ABCD'
    return ''.join(letters[:length])

class ModelsTestCase(TestCase):
    def setUp(self):
        # Usuario y familia base
        self.user = User.objects.create_user(username='u1', password='pass')
        self.familia = Familia.objects.create(nombre='Familiar', administrador=self.user)

    # --- TipoComida ---
    def test_tipo_comida_str_and_validator(self):
        nombre = f"Desayuno{random_letters()}"
        tc = TipoComida(nombre=nombre)
        tc.full_clean()  # debe pasar
        tc.save()
        self.assertEqual(str(tc), nombre)
        # nombre con caracteres inválidos
        bad = TipoComida(nombre='Desayuno123')
        with self.assertRaises(ValidationError):
            bad.full_clean()

    # --- Familia ---
    def test_familia_codigo_invitacion_generated(self):
        f = Familia.objects.create(nombre='Clan')
        self.assertIsNotNone(f.codigo_invitacion)
        self.assertEqual(len(f.codigo_invitacion), 8)
        # si guardo de nuevo, no cambia
        old = f.codigo_invitacion
        f.save()
        self.assertEqual(f.codigo_invitacion, old)

    def test_familia_str(self):
        self.assertEqual(str(self.familia), 'Familiar')

    # --- Ingrediente ---
    def test_ingrediente_str_and_validators(self):
        # eliminamos caracteres inválidos para pasar regex
        ing = Ingrediente(nombre='Leche 2 ñ', frec=2, familia=self.familia)
        ing.full_clean()
        ing.save()
        self.assertEqual(str(ing), 'Leche 2 ñ')
        # frec menor que 1
        bad = Ingrediente(nombre='Agua', frec=0, familia=self.familia)
        with self.assertRaises(ValidationError):
            bad.full_clean()
        # nombre inválido (solo símbolos)
        bad2 = Ingrediente(nombre='!@@@', frec=1, familia=self.familia)
        with self.assertRaises(ValidationError):
            bad2.full_clean()

    def test_delete_ingrediente_cascades_recetas(self):
        ing = Ingrediente.objects.create(nombre='Sal', frec=1, familia=self.familia)
        nombre_tc = random_letters()
        tc = TipoComida.objects.create(nombre=nombre_tc)
        r = Receta.objects.create(
            nombre='Rec1', proteinas=5, carbohidratos=10, familia=self.familia
        )
        r.tipo_comida.add(tc)
        r.ingredientes.add(ing)
        # existía la receta
        self.assertEqual(Receta.objects.count(), 1)
        # al borrar ingrediente, la receta desaparece
        ing.delete()
        self.assertEqual(Receta.objects.count(), 0)

    # --- Receta ---
    def test_receta_str_and_validators(self):
        r = Receta(
            nombre='Tortilla 3 huevos', proteinas=12, carbohidratos=5,
            familia=self.familia
        )
        r.full_clean()
        r.save()
        self.assertEqual(str(r), 'Tortilla 3 huevos')
        # proteinas negativas
        r2 = Receta(
            nombre='Fallida', proteinas=-1, carbohidratos=0, familia=self.familia
        )
        with self.assertRaises(ValidationError):
            r2.full_clean()
        # nombre inválido
        r3 = Receta(
            nombre='@@@', proteinas=0, carbohidratos=0, familia=self.familia
        )
        with self.assertRaises(ValidationError):
            r3.full_clean()

    def test_receta_cascade_on_familia_delete(self):
        r = Receta.objects.create(
            nombre='Pasta', proteinas=0, carbohidratos=30, familia=self.familia
        )
        self.familia.delete()
        self.assertEqual(Receta.objects.count(), 0)

    # --- Calendario y Calendario_Receta ---
    def test_calendario_unique_together(self):
        fecha = datetime.date.today()
        Calendario.objects.create(familia=self.familia, fecha=fecha)
        with self.assertRaises(IntegrityError):
            Calendario.objects.create(familia=self.familia, fecha=fecha)

    def test_calculo_consumos_y_restantes(self):
        nombre_tc = f"Almuerzo{random_letters()}"
        tc = TipoComida.objects.create(nombre=nombre_tc)
        r = Receta.objects.create(
            nombre='Ensalada', proteinas=8, carbohidratos=15, familia=self.familia
        )
        r.tipo_comida.add(tc)
        cal = Calendario.objects.create(familia=self.familia, fecha=datetime.date.today())
        # al principio no hay consumo
        self.assertEqual(cal.proteinas_consumidas, 0)
        self.assertEqual(cal.carbohidratos_consumidos, 0)
        self.assertEqual(cal.calcular_proteinas_restantes(), cal.objetivo_proteico)
        # asignar receta
        cal.asignar_receta(r, tc)
        # consumo debe reflejar la receta
        self.assertEqual(cal.proteinas_consumidas, 8)
        self.assertEqual(cal.carbohidratos_consumidos, 15)
        self.assertEqual(cal.calcular_proteinas_restantes(), cal.objetivo_proteico - 8)
        self.assertEqual(cal.calcular_carbos_restantes(), cal.objetivo_carbohidratos - 15)
        # eliminar receta
        cal.eliminar_receta(r, tc)
        self.assertEqual(cal.proteinas_consumidas, 0)

    def test_calendario_receta_unique(self):
        nombre_tc = f"Merienda{random_letters()}"
        tc = TipoComida.objects.create(nombre=nombre_tc)
        r = Receta.objects.create(
            nombre='Fruta', proteinas=1, carbohidratos=10, familia=self.familia
        )
        cal = Calendario.objects.create(familia=self.familia, fecha=timezone.now().date())
        Calendario_Receta.objects.create(calendario=cal, receta=r, tipo_comida=tc)
        with self.assertRaises(IntegrityError):
            Calendario_Receta.objects.create(calendario=cal, receta=r, tipo_comida=tc)

    def test_calendario_str(self):
        cal = Calendario.objects.create(familia=self.familia, fecha=timezone.now().date())
        s = str(cal)
        self.assertIn(str(self.familia), s)
        self.assertIn(str(cal.fecha), s)

    # --- ListaCompra y ListaCompraItem ---
    def test_lista_compra_str_and_default(self):
        lc = ListaCompra.objects.create(familia=self.familia)
        texto = str(lc)
        self.assertIn('Lista de la compra', texto)
        # start_date por defecto: comparamos solo la fecha
        self.assertEqual(lc.start_date.date(), timezone.now().date())

    def test_lista_compra_item_unique_and_str(self):
        ing = Ingrediente.objects.create(nombre='Pan', frec=1, familia=self.familia)
        lc = ListaCompra.objects.create(familia=self.familia)
        item = ListaCompraItem.objects.create(lista=lc, ingrediente=ing, original=2)
        self.assertEqual(str(item), f"{ing.nombre} en {lc}")
        with self.assertRaises(IntegrityError):
            ListaCompraItem.objects.create(lista=lc, ingrediente=ing)

    # --- SolicitudUniónFamilia ---
    def test_solicitud_union_str_and_defaults(self):
        sol = SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia)
        texto = str(sol)
        self.assertIn(self.user.username, texto)
        self.assertIn(self.familia.nombre, texto)
        self.assertIn('pendiente', texto)
        # fecha_solicitud asignada correctamente
        self.assertIsNotNone(sol.fecha_solicitud)


    def test_crear_tipo_comida_valido(self):
        TipoComida.objects.all().delete()
        tipo = TipoComida.objects.create(nombre="Cena")
        self.assertEqual(tipo.nombre, "Cena")

    def test_crear_familia_con_admin_y_miembros(self):
        familia = Familia.objects.create(nombre="MiFamilia", administrador=self.user)
        familia.miembros.add(self.user)
        self.assertIn(self.user, familia.miembros.all())

    def test_ingrediente_valido_guardado_correctamente(self):
        ing = Ingrediente(nombre="Tomate", frec=2, familia=self.familia)
        ing.full_clean()
        ing.save()
        self.assertEqual(str(ing), "Tomate")

    def test_receta_completa_guardada(self):
        TipoComida.objects.all().delete()
        tipo = TipoComida.objects.create(nombre="Desayuno")
        ing = Ingrediente.objects.create(nombre="Huevo", frec=1, familia=self.familia)
        receta = Receta.objects.create(
            nombre="Huevos revueltos", proteinas=10, carbohidratos=5, familia=self.familia
        )
        receta.tipo_comida.add(tipo)
        receta.ingredientes.add(ing)
        self.assertIn(ing, receta.ingredientes.all())
        self.assertIn(tipo, receta.tipo_comida.all())

    def test_crear_lista_compra_item_valido(self):
        lc = ListaCompra.objects.create(familia=self.familia)
        ing = Ingrediente.objects.create(nombre="Pan", frec=1, familia=self.familia)
        item = ListaCompraItem.objects.create(lista=lc, ingrediente=ing, original=3, compra=2, despensa=1)
        self.assertEqual(item.original, 3)

    def test_solicitud_union_valida(self):
        solicitud = SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia)
        self.assertEqual(solicitud.estado, "pendiente")

    def test_tipo_comida_nombre_invalido_con_numeros(self):
        TipoComida.objects.all().delete()
        with self.assertRaises(ValidationError):
            tipo = TipoComida(nombre="Desayuno123")
            tipo.full_clean()

    def test_ingrediente_nombre_con_simbolos(self):
        with self.assertRaises(ValidationError):
            ing = Ingrediente(nombre="$$$", frec=1, familia=self.familia)
            ing.full_clean()

    def test_ingrediente_frecuencia_negativa(self):
        with self.assertRaises(ValidationError):
            ing = Ingrediente(nombre="Arroz", frec=0, familia=self.familia)
            ing.full_clean()

    def test_receta_nombre_invalido(self):
        with self.assertRaises(ValidationError):
            receta = Receta(nombre="###", proteinas=1, carbohidratos=2, familia=self.familia)
            receta.full_clean()

    def test_receta_proteinas_negativas(self):
        with self.assertRaises(ValidationError):
            receta = Receta(nombre="Test", proteinas=-5, carbohidratos=0, familia=self.familia)
            receta.full_clean()

    def test_calendario_fecha_duplicada_para_familia(self):
        fecha = timezone.now().date()
        Calendario.objects.create(fecha=fecha, familia=self.familia)
        with self.assertRaises(IntegrityError):
            Calendario.objects.create(fecha=fecha, familia=self.familia)

    def test_lista_compra_item_duplicado(self):
        lc = ListaCompra.objects.create(familia=self.familia)
        ing = Ingrediente.objects.create(nombre="Agua", frec=1, familia=self.familia)
        ListaCompraItem.objects.create(lista=lc, ingrediente=ing)
        with self.assertRaises(IntegrityError):
            ListaCompraItem.objects.create(lista=lc, ingrediente=ing)

