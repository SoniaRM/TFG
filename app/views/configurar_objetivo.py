from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from ..models import Calendario, SolicitudUniónFamilia

from ..forms import ObjetivoDiarioForm
from django.contrib.auth.decorators import login_required

#Configuración objetivo diario
@login_required
def vista_configurar_objetivo(request):
    familia = request.user.familias.first()  
    hoy = timezone.now().date()
    calendario, _ = Calendario.objects.get_or_create(fecha=hoy, familia=familia)
    solicitudes = SolicitudUniónFamilia.objects.filter(
        estado='pendiente',
        familia__administrador=request.user
    )
    if request.method == 'POST':
        form = ObjetivoDiarioForm(request.POST, instance=calendario)
        if form.is_valid():
            datos = form.cleaned_data
            Calendario.objects.filter(fecha__gte=hoy, familia=familia).update(
                objetivo_proteico=datos['objetivo_proteico'],
                objetivo_carbohidratos=datos['objetivo_carbohidratos']
            )
            return render(request, 'configurar_objetivo.html', {'form': form, 'exito': True, 'solicitudes': solicitudes})  # Mostrar modal
    else:
        form = ObjetivoDiarioForm(instance=calendario)

    return render(request, 'configurar_objetivo.html', {'form': form,'solicitudes': solicitudes})
