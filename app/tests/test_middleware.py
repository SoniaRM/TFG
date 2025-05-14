from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from app.middleware import CheckFamilyMiddleware
from app.models import Familia, SolicitudUniónFamilia

class MiddlewareTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CheckFamilyMiddleware(lambda req: None)
        self.user = User.objects.create_user(username='testuser', password='12345')

    def test_redirect_usuario_sin_familia_con_solicitud_pendiente(self):
        familia = Familia.objects.create(nombre="FamiliaTest", administrador=self.user)
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=familia, estado='pendiente')

        request = self.factory.get('/some_protected_path/')
        request.user = self.user

        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('esperando_aprobacion'))

    def test_redirect_usuario_sin_familia_sin_solicitud(self):
        request = self.factory.get('/some_protected_path/')
        request.user = self.user

        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('eliminado_familia'))

    def test_no_redirect_usuario_con_familia(self):
        familia = Familia.objects.create(nombre="TestFamily", administrador=self.user)
        familia.miembros.add(self.user)

        request = self.factory.get('/some_protected_path/')
        request.user = self.user

        response = self.middleware(request)
        self.assertIsNone(response)

    def test_no_redirect_rutas_permitidas(self):
        allowed_paths = [
            reverse('login'),
            reverse('signup'),
            reverse('eliminado_familia'),
            reverse('esperando_aprobacion'),
            reverse('logout'),
            reverse('reenviar_solicitud'),
            reverse('crear_familia'),
        ]
        for path in allowed_paths:
            request = self.factory.get(path)
            request.user = self.user

            response = self.middleware(request)
            self.assertIsNone(response)

    def test_usuario_con_familia_acceso_ruta_permitida_no_redirige(self):
        familia = Familia.objects.create(nombre="PermittedFamily", administrador=self.user)
        familia.miembros.add(self.user)

        for path in [
            reverse('login'),
            reverse('signup'),
            reverse('eliminado_familia'),
            reverse('esperando_aprobacion'),
            reverse('logout'),
            reverse('reenviar_solicitud'),
            reverse('crear_familia'),
        ]:
            request = self.factory.get(path)
            request.user = self.user
            response = self.middleware(request)
            self.assertIsNone(response)

    def test_usuario_sin_familia_sin_solicitud_en_ruta_permitida_no_redirige(self):
        request = self.factory.get(reverse('login'))
        request.user = self.user
        response = self.middleware(request)
        self.assertIsNone(response)

    def test_usuario_con_familia_ruta_protegida_no_redirige(self):
        familia = Familia.objects.create(nombre="RutaProtegida", administrador=self.user)
        familia.miembros.add(self.user)
        request = self.factory.get('/zona-privada/')
        request.user = self.user
        response = self.middleware(request)
        self.assertIsNone(response)

    def test_usuario_sin_familia_con_solicitud_rechazada_redirige_a_eliminado(self):
        familia = Familia.objects.create(nombre="Rechazo", administrador=self.user)
        SolicitudUniónFamilia.objects.create(usuario=self.user, familia=familia, estado='rechazada')

        request = self.factory.get('/zona-protegida/')
        request.user = self.user

        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('eliminado_familia'))

    def test_middleware_sigue_chain_si_no_redirige(self):
        marcado = {"llamado": False}
        def fake_get_response(request):
            marcado["llamado"] = True
            return None

        middleware = CheckFamilyMiddleware(fake_get_response)
        familia = Familia.objects.create(nombre="ChainFamily", administrador=self.user)
        familia.miembros.add(self.user)

        request = self.factory.get('/algo/')
        request.user = self.user
        middleware(request)
        self.assertTrue(marcado["llamado"])

