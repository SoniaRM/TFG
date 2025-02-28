#encoding:utf-8
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models

class TipoComida(models.Model):
    nombre = models.CharField(
        max_length=20, 
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]+$',  # Defining the regex as a raw string
                message='El nombre solo puede contener letras.',
                code='invalid_nombre'
            )
        ], 
        unique=True)

    def __str__(self):
        return self.nombre

class Ingrediente(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]+$',  # Defining the regex as a raw string
                message='El nombre solo puede contener letras y espacios.',
                code='invalid_nombre'
            )
        ]
    )
    frec = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return self.nombre

class Receta(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]+$',  # Defining the regex as a raw string
                message='El nombre solo puede contener letras y espacios.',
                code='invalid_nombre'
            )
        ]
    )
    tipo_comida = models.ManyToManyField(TipoComida, related_name='recetas')
    proteinas = models.IntegerField(validators=[MinValueValidator(0)])
    ingredientes = models.ManyToManyField(Ingrediente, related_name='recetas')

    def __str__(self):
        return self.nombre

