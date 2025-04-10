from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from ..forms import CustomSignupForm, ChangeFamilyForm, ReenviarSolicitudForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from ..models import Familia, SolicitudUniónFamilia
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


class SignupView(CreateView):
    form_class = CustomSignupForm
    template_name = 'colaborativo/signup.html'
    success_url = reverse_lazy('listado_recetas')  # O la URL a la que desees redirigir

    def form_valid(self, form):
        response = super().form_valid(form)
        # Loguear al usuario automáticamente
        login(self.request, self.object)
        accion = form.cleaned_data.get("accion_familiar")
        # Si la acción es unirse, redirige a la vista de "esperando aprobación"
        if accion == "unirse":
            self.success_url = reverse_lazy('esperando_aprobacion')
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
                if familia:
                    # En lugar de agregar el usuario directamente, crea una solicitud pendiente.
                    SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
                
            # Para que el usuario pertenezca únicamente a una familia, limpiamos sus asociaciones actuales:
            user.familias.clear()
            user.familias.add(familia)
            return redirect('listado_recetas')
    else:
        form = ChangeFamilyForm()
    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})


@login_required
def lista_solicitudes_familia(request):
    # Sólo se muestran las solicitudes de la(s) familia(s) donde el usuario es administrador.
    solicitudes = SolicitudUniónFamilia.objects.filter(
        estado='pendiente',
        familia__administrador=request.user
    )
    return render(request, 'colaborativo/lista_solicitudes.html', {'solicitudes': solicitudes})

@login_required
def aprobar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudUniónFamilia, id=solicitud_id)
    # Verifica que el usuario que aprueba sea el administrador de la familia.
    if solicitud.familia.administrador != request.user:
        # Si no es administrador, podrías devolver un error o redirigir
        return redirect('lista_solicitudes_familia')
    solicitud.familia.miembros.add(solicitud.usuario)
    solicitud.estado = 'aprobada'
    solicitud.save()
    return redirect('lista_solicitudes_familia')

@login_required
def rechazar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudUniónFamilia, id=solicitud_id)
    # Verifica que solo el administrador pueda rechazar la solicitud
    if solicitud.familia.administrador != request.user:
        return redirect('lista_solicitudes_familia')
    solicitud.estado = 'rechazada'
    solicitud.save()
    # Se podría redirigir a una página donde se notifique al usuario que su solicitud fue rechazada
    return redirect('lista_solicitudes_familia')

@login_required
def esperando_aprobacion(request):
    # Se busca la solicitud pendiente del usuario.
    solicitud = SolicitudUniónFamilia.objects.filter(usuario=request.user).order_by('-fecha_solicitud').first()
    return render(request, 'colaborativo/esperando_aprobacion.html', {'solicitud': solicitud})

@login_required
def reenviar_solicitud(request):
    if request.method == "POST":
        form = ReenviarSolicitudForm(request.POST)
        if form.is_valid():
            familia = form.cleaned_data["familia_existente"]
            # Opcional: Si ya tienes una solicitud rechazada, puedes eliminarla o actualizarla.
            # Aquí creamos una nueva solicitud con estado "pendiente"
            SolicitudUniónFamilia.objects.create(usuario=request.user, familia=familia)
            messages.success(request, "Solicitud enviada nuevamente. Espera a que sea aprobada.")
            return redirect("esperando_aprobacion")
    else:
        form = ReenviarSolicitudForm()

    return render(request, "colaborativo/reenviar_solicitud.html", {"form": form})