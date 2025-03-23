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
#from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    #path('admin/', admin.site.urls),
    #RECETAS
    path('', views.listado_recetas, name='listado_recetas'),
    path('recetas/', views.listado_recetas, name='listado_recetas'),
    path('recetas/<int:pk>/', views.detalle_receta, name='detalle_receta'),
    path('recetas/crear/', views.crear_receta, name='crear_receta'),
    path('recetas/editar/<int:pk>/', views.editar_receta, name='editar_receta'),  # Nueva ruta para editar recetas

    #INGREDIENTES
    path('ingredientes/', views.listado_ingredientes, name='listado_ingredientes'),
    path('ingredientes/<int:pk>/', views.detalle_ingrediente, name='detalle_ingrediente'),
    path('ingredientes/crear/', views.crear_ingrediente, name='crear_ingrediente'),
    path('ingredientes/editar/<int:pk>/', views.editar_ingrediente, name='editar_ingrediente'),

    #CALENDARIO
    #path("api/calendario_eventos/", views.calendario_eventos, name="calendario_eventos"), #Lista de las recetas añadidas al calendario y con tipoComida
    #path("calendario/", views.vista_calendario, name="vista_calendario"), #Vista del calendario
    #path("api/agregar_receta_calendario/", views.agregar_receta_calendario, name="agregar_receta_calendario"), #Añadir receta al calendario

    path("calendario_semanal/", views.calendario_semanal, name="calendario_semanal"),
    path("api/recetas_por_tipo/", views.recetas_por_tipo, name="recetas_por_tipo"),
    path("api/agregar_receta_calendario/", views.agregar_receta_calendario, name="agregar_receta_calendario"),
    path("api/recetas_en_calendario/", views.recetas_en_calendario, name="recetas_en_calendario"),
    path("api/eliminar_receta_calendario/", views.eliminar_receta_calendario, name="eliminar_receta_calendario"),
    path("api/calendario_dia/", views.actualizar_calendario_dia, name="actualizar_calendario_dia"),
    path('api/dia/<str:fecha>/', views.datos_dia, name='datos_dia'),

    #EXPORTACIÓN
    path('exportar_semana/', views.exportar_semana, name='exportar_semana'),

    #LISTA COMPRA
    path('lista_compra/', views.lista_compra, name='lista_compra'),
    path('lista_compra/datos', views.lista_compra_datos, name='lista_compra_datos'),
    path('mover_compra_despensa/', views.mover_compra_despensa, name='mover_compra_despensa'),
    path('mover_despensa_compra/', views.mover_despensa_compra, name='mover_despensa_compra'),
  

]
