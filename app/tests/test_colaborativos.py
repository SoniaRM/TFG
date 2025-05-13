from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app.models import Familia, SolicitudUniónFamilia

class ColaborativosViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.familia = Familia.objects.create(nombre="TestFamilia", administrador=self.user)
        self.familia.miembros.add(self.user)
        self.client.login(username="testuser", password="12345")

    def test_cambiar_familia_crear_valida(self):
        data = {
            'accion_familiar': 'crear',
            'nombre_familia': 'familianueva'
        }
        response = self.client.post(reverse("cambiar_familia"), data)
        self.assertRedirects(response, reverse("listado_recetas"))
        self.assertTrue(Familia.objects.filter(nombre='familianueva').exists())
    
    def test_cambiar_familia_crear_nombre_duplicado(self):
        Familia.objects.create(nombre="duplicado", administrador=self.user)
        data = {
            'accion_familiar': 'crear',
            'nombre_familia': 'Duplicado'  # En mayúscula para verificar que se hace lower
        }
        response = self.client.post(reverse('cambiar_familia'), data, follow=True)
        form = response.context['form']
        self.assertFormError(form, 'nombre_familia', 'Esa familia ya existe, por favor elige otro nombre.')

    def test_cambiar_familia_get(self):
        response = self.client.get(reverse("cambiar_familia"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/cambiar_familia.html")
        self.assertIn("form", response.context)

    def test_aprobar_solicitud_valida(self):
        nuevo = User.objects.create_user(username="nuevo", password="12345")
        solicitud = SolicitudUniónFamilia.objects.create(usuario=nuevo, familia=self.familia, estado='pendiente')
        response = self.client.get(reverse('aprobar_solicitud', args=[solicitud.id]))
        self.assertRedirects(response, reverse('configurar_objetivo'))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertIn(self.familia, nuevo.familias.all())

    def test_aprobar_solicitud_usuario_no_admin(self):
        otro_admin = User.objects.create_user(username="otroadmin", password="12345")
        otra_familia = Familia.objects.create(nombre="Otra", administrador=otro_admin)
        solicitud = SolicitudUniónFamilia.objects.create(usuario=self.user, familia=otra_familia, estado='pendiente')
        response = self.client.get(reverse('aprobar_solicitud', args=[solicitud.id]))
        self.assertRedirects(response, reverse('configurar_objetivo'))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')  # No debería cambiar

    def test_rechazar_solicitud_valida(self):
        nuevo = User.objects.create_user(username="nuevo2", password="12345")
        solicitud = SolicitudUniónFamilia.objects.create(usuario=nuevo, familia=self.familia, estado='pendiente')
        response = self.client.get(reverse('rechazar_solicitud', args=[solicitud.id]))
        self.assertRedirects(response, reverse('configurar_objetivo'))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')

    def test_rechazar_solicitud_usuario_no_admin(self):
        otro_admin = User.objects.create_user(username="otroadmin2", password="12345")
        otra_familia = Familia.objects.create(nombre="Distinta", administrador=otro_admin)
        solicitud = SolicitudUniónFamilia.objects.create(usuario=self.user, familia=otra_familia, estado='pendiente')
        response = self.client.get(reverse('rechazar_solicitud', args=[solicitud.id]))
        self.assertRedirects(response, reverse('configurar_objetivo'))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')  # No se debería haber rechazado

    def test_esperando_aprobacion_redirige_si_aprobada(self):
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia, estado='aprobada')
        response = self.client.get(reverse('esperando_aprobacion'))
        self.assertRedirects(response, reverse('listado_recetas'))

    def test_esperando_aprobacion_renderiza_template_si_pendiente(self):
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia, estado='pendiente')
        response = self.client.get(reverse('esperando_aprobacion'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'colaborativo/esperando_aprobacion.html')

    def test_reenviar_solicitud_post_crea_solicitud(self):
        nueva_familia = Familia.objects.create(nombre="NuevaFam", administrador=self.user)
        data = {"familia_existente": nueva_familia.codigo_invitacion}
        response = self.client.post(reverse("reenviar_solicitud"), data)
        self.assertRedirects(response, reverse("esperando_aprobacion"))
        self.assertTrue(SolicitudUniónFamilia.objects.filter(usuario=self.user, familia=nueva_familia).exists())

    def test_esperando_aprobacion_renderiza_template_si_no_aprobada(self):
        # No hay solicitud o no está aprobada
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia, estado='pendiente')
        response = self.client.get(reverse('esperando_aprobacion'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'colaborativo/esperando_aprobacion.html')
        self.assertIn('solicitud', response.context)

    def test_esperando_aprobacion_redirige_si_aprobada(self):
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=self.familia, estado='aprobada')
        response = self.client.get(reverse('esperando_aprobacion'))
        self.assertRedirects(response, reverse('listado_recetas'))

    def test_reenviar_solicitud_get_muestra_formulario(self):
        response = self.client.get(reverse("reenviar_solicitud"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/reenviar_solicitud.html")
        self.assertIn("form", response.context)

    def test_reenviar_solicitud_post_valido_crea_solicitud(self):
        nueva_familia = Familia.objects.create(nombre="FamiliaX", administrador=self.user)
        form_data = {"familia_existente": nueva_familia.codigo_invitacion}
        response = self.client.post(reverse("reenviar_solicitud"), data=form_data)
        self.assertRedirects(response, reverse("esperando_aprobacion"))
        self.assertTrue(SolicitudUniónFamilia.objects.filter(usuario=self.user, familia=nueva_familia).exists())

    def test_eliminar_miembro_exitosa(self):
        otro = User.objects.create_user(username="otro", password="12345")
        self.familia.miembros.add(otro)
        response = self.client.post(reverse("eliminar_miembro", args=[otro.id]))
        self.assertRedirects(response, reverse("configurar_objetivo"))
        self.assertNotIn(otro, self.familia.miembros.all())

    def test_eliminar_miembro_no_puede_autoeiminarse(self):
        response = self.client.post(reverse("eliminar_miembro", args=[self.user.id]))
        self.assertRedirects(response, reverse("configurar_objetivo"))
        self.assertIn(self.user, self.familia.miembros.all())

    def test_eliminado_familia_get_muestra_formulario(self):
        response = self.client.get(reverse("eliminado_familia"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/eliminado_familia.html")
        self.assertIn("form", response.context)

    def test_eliminado_familia_post_crear_nueva_familia(self):
        self.user.familias.clear()
        form_data = {
            "accion_familiar": "crear",
            "nombre_familia": "nueva123"
        }
        response = self.client.post(reverse("eliminado_familia"), data=form_data)
        self.assertRedirects(response, reverse("listado_recetas"))
        self.assertTrue(Familia.objects.filter(nombre="nueva123").exists())

    def test_eliminado_familia_post_unirse_con_codigo_valido(self):
        self.user.familias.clear()
        nueva = Familia.objects.create(nombre="otra", administrador=self.user)
        form_data = {
            "accion_familiar": "unirse",
            "codigo_invitacion": nueva.codigo_invitacion
        }
        response = self.client.post(reverse("eliminado_familia"), data=form_data)
        self.assertRedirects(response, reverse("esperando_aprobacion"))
        self.assertTrue(SolicitudUniónFamilia.objects.filter(usuario=self.user, familia=nueva).exists())

    def test_eliminado_familia_post_unirse_codigo_invalido(self):
        self.user.familias.clear()
        form_data = {
            "accion_familiar": "unirse",
            "codigo_invitacion": "invalido123"
        }
        response = self.client.post(reverse("eliminado_familia"), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/eliminado_familia.html")

    def test_crear_familia_post_valido(self):
        response = self.client.post(reverse("crear_familia"), data={"nombre_familia": "familia123"})
        self.assertRedirects(response, reverse("listado_recetas"))
        self.assertTrue(Familia.objects.filter(nombre="familia123").exists())

    def test_crear_familia_get_devuelve_template(self):
        response = self.client.get(reverse("crear_familia"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/crear_familia.html")

    def test_crear_familia_post_nombre_vacio(self):
        response = self.client.post(reverse("crear_familia"), data={"nombre_familia": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/crear_familia.html")
        self.assertFalse(Familia.objects.filter(administrador=self.user, nombre="").exists())

    def test_crear_familia_post_nombre_duplicado(self):
        Familia.objects.create(nombre="familia123", administrador=self.user)
        response = self.client.post(reverse("crear_familia"), data={"nombre_familia": "familia123"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "colaborativo/crear_familia.html")

    def test_crear_familia_post_valido(self):
        response = self.client.post(reverse("crear_familia"), data={"nombre_familia": "nuevaFamilia"})
        self.assertRedirects(response, reverse("listado_recetas"))
        self.assertTrue(Familia.objects.filter(nombre="nuevafamilia", administrador=self.user).exists())
        self.assertIn(self.familia.administrador, User.objects.filter(familias__nombre="nuevafamilia"))
