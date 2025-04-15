from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from ..forms import CustomSignupForm, ChangeFamilyForm, ReenviarSolicitudForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from ..models import Familia, SolicitudUniónFamilia
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model

#Para eliminar_miembro
User = get_user_model()


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
                # Se actualiza la familia actual del usuario de forma inmediata
                user.familias.clear()
                user.familias.add(familia)
                messages.success(request, "Familia creada y asignada correctamente.")
                return redirect('listado_recetas')

            elif accion == 'unirse':
                # Aquí se obtiene la familia a la que se quiere unir por el código de invitación
                # Por ejemplo, si en el formulario el campo es 'codigo_invitacion'
                codigo = form.cleaned_data['codigo_invitacion'].strip()
                try:
                    familia = Familia.objects.get(codigo_invitacion=codigo)
                except Familia.DoesNotExist:
                    form.add_error('codigo_invitacion', "No se encontró una familia con este código.")
                    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})
                
                # Opcional: Verificar si ya existe una solicitud pendiente para esa familia
                solicitud_existente = SolicitudUniónFamilia.objects.filter(usuario=user, familia=familia, estado='pendiente').first()
                if solicitud_existente:
                    messages.info(request, "Ya tienes una solicitud pendiente para esta familia.")
                else:
                    # Se crea la solicitud pendiente sin quitarle la familia actual al usuario
                    SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
                    messages.info(request, "Solicitud enviada. Espera a la aprobación del administrador.")
                
                # Se redirige al usuario a la vista de espera de aprobación
                return redirect('esperando_aprobacion')
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
    
    user = solicitud.usuario
    # Si el usuario pertenece a una familia diferente a la de la solicitud aprobada,
    # y era administrador en ella, se debe reasignar el rol de administrador.
    if user.familias.exists():
        current_family = user.familias.first()
        # Verificar que la familia actual no sea ya la de la solicitud aprobada
        if current_family != solicitud.familia and current_family.administrador == user:
            otros_miembros = current_family.miembros.exclude(id=user.id)
            if otros_miembros.exists():
                current_family.administrador = otros_miembros.first()
                current_family.save()
            else:
                # Si no hay otros miembros, puedes decidir dejarlo como administrador
                # o gestionar de otra forma según la lógica de tu aplicación.
                pass

    # Actualiza la relación: elimina las familias actuales y asigna la nueva
    user.familias.clear()
    user.familias.add(solicitud.familia)

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
    if solicitud and solicitud.estado == "aprobada":
        return redirect('listado_recetas')
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

@login_required
def eliminar_miembro(request, miembro_id):
    admin = request.user
    # Se obtiene la familia donde el usuario es administrador.
    # Se asume que tu modelo Familia tiene el campo "administrador" y una relación many-to-many con "miembros"
    familia = get_object_or_404(Familia, administrador=admin)
    
    miembro = get_object_or_404(User, id=miembro_id)
    # Verificar que el usuario a eliminar pertenezca a la familia
    if miembro not in familia.miembros.all():
        messages.error(request, "El usuario seleccionado no pertenece a tu familia.")
        return redirect('configurar_objetivo')  # O la vista donde se liste a los miembros
    
    # Si se desea evitar eliminar al propio administrador:
    if miembro == admin:
        messages.error(request, "No puedes eliminarte a ti mismo.")
        return redirect('configurar_objetivo')
    
    # Remover el miembro de la familia
    familia.miembros.remove(miembro)
    
    # Opcional: Si quieres que, en caso de que el usuario eliminado esté conectado, se le "marque" como eliminado para que al hacer siguiente petición se le redirija a la página correspondiente,
    # puedes implementar un mecanismo basado en una marca en la base de datos o, de forma más sencilla, notificarlo en el mensaje (ver punto 2).
    
    messages.success(request, f"El usuario {miembro.username} ha sido eliminado de la familia.")
    return redirect('configurar_objetivo')
    
@login_required
def eliminado_familia(request):
    user = request.user
    if request.method == 'POST':
        form = ChangeFamilyForm(request.POST)
        if form.is_valid():
            accion = form.cleaned_data['accion_familiar']
            if accion == 'crear':
                # Si el usuario decide crear una nueva familia:
                nombre = form.cleaned_data['nombre_familia'].strip().lower()
                familia, created = Familia.objects.get_or_create(nombre=nombre)
                # Asignar la familia al usuario eliminado:
                user.familias.clear()
                user.familias.add(familia)
                messages.success(request, "Familia creada y asignada correctamente.")
                return redirect('listado_recetas')
            elif accion == 'unirse':
                # Se obtiene el código de invitación y se busca la familia correspondiente.
                codigo = form.cleaned_data['codigo_invitacion'].strip()
                try:
                    familia = Familia.objects.get(codigo_invitacion=codigo)
                except Familia.DoesNotExist:
                    form.add_error('codigo_invitacion', "No se encontró una familia con este código.")
                    return render(request, 'colaborativo/eliminado_familia.html', {'form': form})
                # En lugar de asignar directamente la familia, se crea una solicitud pendiente.
                SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
                messages.info(request, "Solicitud enviada. Espera a que el administrador la apruebe.")
                return redirect('esperando_aprobacion')
    else:
        form = ChangeFamilyForm()

    return render(request, 'colaborativo/eliminado_familia.html', {'form': form})
