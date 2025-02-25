#encoding:utf-8

from django.db import models
from .components import TipoComida

class Ingrediente(models.Model):
    nombre = models.CharField(max_length=100)
    frec = models.IntegerField()

    def __str__(self):
        return self

class Receta(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_comida = models.CharField(max_length=20, choices=TipoComida.TIPOCOMIDA)
    proteinas = models.IntegerField()
    ingredientes = models.ManyToManyField(Ingrediente, related_name='recetas')


    def __str__(self):
        return self.nombre

