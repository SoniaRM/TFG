"""
URL configuration for tfgapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app.views import recetas, ingredientes, calendario, lista_compra, configurar_objetivo, colaborativos
from django.contrib.auth import views as auth_views
from app.views.colaborativos import SignupView, cambiar_familia
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    # RECETAS:
    path('', login_required(recetas.listado_recetas), name='listado_recetas'),
    path('recetas/', login_required(recetas.listado_recetas), name='listado_recetas'),
    path('recetas/<int:pk>/', login_required(recetas.detalle_receta), name='detalle_receta'),
    path('recetas/crear/', login_required(recetas.crear_receta), name='crear_receta'),
    path('recetas/editar/<int:pk>/', login_required(recetas.editar_receta), name='editar_receta'),
    # INGREDIENTES:
    path('ingredientes/', login_required(ingredientes.listado_ingredientes), name='listado_ingredientes'),
    path('ingredientes/<int:pk>/', login_required(ingredientes.detalle_ingrediente), name='detalle_ingrediente'),
    path('ingredientes/crear/', login_required(ingredientes.crear_ingrediente), name='crear_ingrediente'),
    path('ingredientes/editar/<int:pk>/', login_required(ingredientes.editar_ingrediente), name='editar_ingrediente'),
    # CALENDARIO:
    path("calendario_semanal/", login_required(calendario.calendario_semanal), name="calendario_semanal"),
    path("api/recetas_por_tipo/", login_required(calendario.recetas_por_tipo), name="recetas_por_tipo"),
    path("api/agregar_receta_calendario/", login_required(calendario.agregar_receta_calendario), name="agregar_receta_calendario"),
    path("api/recetas_en_calendario/", login_required(calendario.recetas_en_calendario), name="recetas_en_calendario"),
    path("api/eliminar_receta_calendario/", login_required(calendario.eliminar_receta_calendario), name="eliminar_receta_calendario"),
    path("api/calendario_dia/", login_required(calendario.actualizar_calendario_dia), name="actualizar_calendario_dia"),
    path('api/dia/<str:fecha>/', login_required(calendario.datos_dia), name='datos_dia'),
    # EXPORTACIÓN:
    path('exportar_semana/', login_required(calendario.exportar_semana), name='exportar_semana'),
    # LISTA COMPRA:
    path('lista_compra/', login_required(lista_compra.vista_lista_compra), name='lista_compra'),
    path('lista_compra/datos', login_required(lista_compra.lista_compra_datos), name='lista_compra_datos'),
    path('mover_compra_despensa/', login_required(lista_compra.mover_compra_despensa), name='mover_compra_despensa'),
    path('mover_despensa_compra/', login_required(lista_compra.mover_despensa_compra), name='mover_despensa_compra'),
    path('finalizar_compra/', login_required(lista_compra.finalizar_compra), name='finalizar_compra'),
    path('lista_compra/reset/', login_required(lista_compra.resetear_lista_compra), name='reset_lista_compra'),
    path('exportar_lista_compra/', login_required(lista_compra.exportar_lista_compra), name='exportar_lista_compra'),
    # CONFIGURACION OBJETIVO:
    path('configurar_objetivo/', login_required(configurar_objetivo.vista_configurar_objetivo), name='configurar_objetivo'),
    
    #COLABORATIVO
    path('login/', auth_views.LoginView.as_view(template_name='colaborativo/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('cambiar_familia/', cambiar_familia, name='cambiar_familia'),
    path('lista_solicitudes_familia/', colaborativos.lista_solicitudes_familia, name='lista_solicitudes_familia'),
    path('aprobar_solicitud/<int:solicitud_id>/', colaborativos.aprobar_solicitud, name='aprobar_solicitud'),
    path('rechazar_solicitud/<int:solicitud_id>/', colaborativos.rechazar_solicitud, name='rechazar_solicitud'),
    path('esperando_aprobacion/', colaborativos.esperando_aprobacion, name='esperando_aprobacion'),
    path('reenviar_solicitud/', colaborativos.reenviar_solicitud, name='reenviar_solicitud'),

]
