from django.shortcuts import redirect
from django.urls import reverse
from .models import SolicitudUniónFamilia  # Asegúrate de importar el modelo correctamente

class CheckFamilyMiddleware:
    """
    Middleware que redirige a los usuarios autenticados sin familia a la página de "esperando aprobación" 
    si tienen una solicitud pendiente, o a "eliminado_familia" en caso contrario.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            allowed_paths = [
                reverse('login'),
                reverse('signup'),
                reverse('eliminado_familia'),
                reverse('esperando_aprobacion'),
                reverse('logout'),
                reverse('reenviar_solicitud'),
                reverse('cambiar_familia'),
                reverse('crear_familia'),
            ]
            if request.path not in allowed_paths and not request.user.familias.exists():
                # Consultamos directamente el modelo para ver si existe alguna solicitud pendiente.
                if SolicitudUniónFamilia.objects.filter(usuario=request.user, estado='pendiente').exists():
                    return redirect('esperando_aprobacion')
                else:
                    return redirect('eliminado_familia')
        return self.get_response(request)
