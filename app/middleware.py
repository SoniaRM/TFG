from django.shortcuts import redirect
from django.urls import reverse

class CheckFamilyMiddleware:
    """
    Middleware que redirige a los usuarios autenticados que aún no tienen una familia asignada
    a la página de "esperando aprobación".
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Definir las rutas permitidas donde el usuario sin familia puede acceder.
            # Estas rutas no se validan; por ejemplo: logout, login, signup y la de esperar aprobación.
            allowed_paths = [
                reverse('login'),
                reverse('signup'),
                reverse('esperando_aprobacion'),
                reverse('logout'),
                reverse('reenviar_solicitud'),

                # Puedes agregar otras URLs permitidas, por ejemplo, para recursos estáticos si es necesario.
            ]
            # Si la URL actual no es una de las permitidas y el usuario no tiene una familia...
            if request.path not in allowed_paths and not request.user.familias.exists():
                return redirect('esperando_aprobacion')
        return self.get_response(request)
