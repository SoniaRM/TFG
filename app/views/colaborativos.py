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
    success_url = reverse_lazy('listado_recetas') 

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        accion = form.cleaned_data.get("accion_familiar")
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
                nombre_familia = form.cleaned_data['nombre_familia'].strip().lower()
                if Familia.objects.filter(nombre=nombre_familia).exists():
                    form.add_error('nombre_familia', 'Esa familia ya existe, por favor elige otro nombre.')
                    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})
                for f in user.familias.all():
                    if f.administrador == user:
                        nuevo_admin = f.miembros.exclude(id=user.id).first()
                        if nuevo_admin:
                            f.administrador = nuevo_admin
                            f.save()

                familia = Familia.objects.create(nombre=nombre_familia, administrador=user)
                user.familias.clear()
                user.familias.add(familia)
                messages.success(request, "Familia creada y asignada correctamente. Ahora eres el administrador.")
                return redirect('listado_recetas')

            elif accion == 'unirse':
                codigo = form.cleaned_data['codigo_invitacion'].strip()
                try:
                    familia = Familia.objects.get(codigo_invitacion=codigo)
                except Familia.DoesNotExist:
                    form.add_error('codigo_invitacion', "No se encontró una familia con este código.")
                    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})
                
                solicitud_existente = SolicitudUniónFamilia.objects.filter(usuario=user, familia=familia, estado='pendiente').first()
                if solicitud_existente:
                    messages.info(request, "Ya tienes una solicitud pendiente para esta familia.")
                else:
                    SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
                    messages.info(request, "Solicitud enviada. Espera a la aprobación del administrador.")
                
                return redirect('esperando_aprobacion')
    else:
        form = ChangeFamilyForm()
    return render(request, 'colaborativo/cambiar_familia.html', {'form': form})

@login_required
def aprobar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudUniónFamilia, id=solicitud_id)
    if solicitud.familia.administrador != request.user:
        return redirect('configurar_objetivo')
    
    user = solicitud.usuario
    if user.familias.exists():
        current_family = user.familias.first()
        if current_family != solicitud.familia and current_family.administrador == user:
            otros_miembros = current_family.miembros.exclude(id=user.id)
            if otros_miembros.exists():
                current_family.administrador = otros_miembros.first()
                current_family.save()
            else:
                pass

    user.familias.clear()
    user.familias.add(solicitud.familia)

    solicitud.estado = 'aprobada'
    solicitud.save()
    return redirect('configurar_objetivo')

@login_required
def rechazar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudUniónFamilia, id=solicitud_id)
    if solicitud.familia.administrador != request.user:
        return redirect('configurar_objetivo')
    solicitud.estado = 'rechazada'
    solicitud.save()
    return redirect('configurar_objetivo')

@login_required
def esperando_aprobacion(request):
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
            SolicitudUniónFamilia.objects.create(usuario=request.user, familia=familia)
            messages.success(request, "Solicitud enviada nuevamente. Espera a que sea aprobada.")
            return redirect("esperando_aprobacion")
    else:
        form = ReenviarSolicitudForm()

    return render(request, "colaborativo/reenviar_solicitud.html", {"form": form})

@login_required
def eliminar_miembro(request, miembro_id):
    admin = request.user
    miembro = get_object_or_404(User, id=miembro_id)
    familia = get_object_or_404(Familia, administrador=admin, miembros=miembro)
    miembro = get_object_or_404(User, id=miembro_id)

    if miembro not in familia.miembros.all():
        messages.error(request, "El usuario seleccionado no pertenece a tu familia.")
        return redirect('configurar_objetivo')  
    
    if miembro == admin:
        messages.error(request, "No puedes eliminarte a ti mismo.")
        return redirect('configurar_objetivo')
    
    familia.miembros.remove(miembro)
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
                nombre_familia = form.cleaned_data['nombre_familia'].strip().lower()
                if Familia.objects.filter(nombre=nombre_familia).exists():
                    form.add_error('nombre_familia', 'Esa familia ya existe, por favor elige otro nombre.')
                    return render(request, 'colaborativo/eliminado_familia.html', {'form': form})
                familia = Familia.objects.create(nombre=nombre_familia, administrador=user)
                user.familias.clear()
                user.familias.add(familia)
                messages.success(request, "Familia creada y asignada correctamente. Ahora eres el administrador.")
                return redirect('listado_recetas')

            elif accion == 'unirse':
                codigo = form.cleaned_data['codigo_invitacion'].strip()
                try:
                    familia = Familia.objects.get(codigo_invitacion=codigo)
                except Familia.DoesNotExist:
                    form.add_error('codigo_invitacion', "No se encontró una familia con este código.")
                    return render(request, 'colaborativo/eliminado_familia.html', {'form': form})
                SolicitudUniónFamilia.objects.create(usuario=user, familia=familia)
                messages.info(request, "Solicitud enviada. Espera a que el administrador la apruebe.")
                return redirect('esperando_aprobacion')
    else:
        form = ChangeFamilyForm()

    return render(request, 'colaborativo/eliminado_familia.html', {'form': form})


@login_required
def crear_familia(request):
    if request.method == 'POST':
        nombre_familia = request.POST.get("nombre_familia", "").strip().lower()
        if not nombre_familia:
            messages.error(request, "El nombre de la familia es obligatorio.")
            return render(request, "colaborativo/crear_familia.html")
        
        if Familia.objects.filter(nombre=nombre_familia).exists():
            messages.error(request, "Ya existe una familia con ese nombre, por favor elige otro nombre.")
            return render(request, "colaborativo/crear_familia.html")
        
        familia = Familia.objects.create(nombre=nombre_familia, administrador=request.user)
        
        request.user.familias.clear()
        request.user.familias.add(familia)
        
        messages.success(request, "Familia creada y asignada correctamente. Ahora eres el administrador.")
        return redirect("listado_recetas")
    
    return render(request, "colaborativo/crear_familia.html")