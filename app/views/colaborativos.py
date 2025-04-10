from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from ..forms import CustomSignupForm, ChangeFamilyForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from ..models import Familia
from django.shortcuts import render, redirect

class SignupView(CreateView):
    form_class = CustomSignupForm
    template_name = 'colaborativo/signup.html'
    success_url = reverse_lazy('listado_recetas')  # O la URL a la que desees redirigir

    def form_valid(self, form):
        response = super().form_valid(form)
        # Loguear al usuario automáticamente
        login(self.request, self.object)
        return response


@login_required
def cambiar_familia(request):
    user = request.user
    if request.method == 'POST':
        form = ChangeFamilyForm(request.POST)
        if form.is_valid():
            accion = form.cleaned_data['accion_familiar']
            if accion == 'crear':
                # Se crea (o se obtiene) la familia con el nombre ingresado (se fuerza a minúsculas si así lo deseas)
                familia, created = Familia.objects.get_or_create(
                    nombre=form.cleaned_data['nombre_familia'].strip().lower()
                )
            elif accion == 'unirse':
                familia = form.cleaned_data['familia_unirse']
            # Para que el usuario pertenezca únicamente a una familia, limpiamos sus asociaciones actuales:
            user.familias.clear()
            user.familias.add(familia)
            return redirect('listado_recetas')
    else:
        form = ChangeFamilyForm()
    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})
