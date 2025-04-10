#encoding:utf-8
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid

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

class Familia(models.Model):
    nombre = models.CharField(max_length=100)
    # Se genera un código único de invitación si aún no existe.
    codigo_invitacion = models.CharField(max_length=8, unique=True, blank=True)
    miembros = models.ManyToManyField(User, related_name='familias')

    def save(self, *args, **kwargs):
        if not self.codigo_invitacion:
            # Genera un código aleatorio de 8 caracteres
            self.codigo_invitacion = uuid.uuid4().hex[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Ingrediente(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ,\s]+$',
                message='El nombre solo puede contener letras, números, espacios, comas y la letra ñ.',
                code='invalid_nombre'
            )
        ]
    )
    frec = models.IntegerField(validators=[MinValueValidator(1)])
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='ingredientes')

    def __str__(self):
        return self.nombre

    def delete(self, *args, **kwargs):
        # Elimina todas las recetas que contienen este ingrediente
        self.recetas.all().delete()
        # Llama al método delete original para borrar el ingrediente
        super().delete(*args, **kwargs)

class Receta(models.Model):
    nombre = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ,\s]+$',
                message='El nombre solo puede contener letras, números, espacios, comas y la letra ñ.',
                code='invalid_nombre'
            )
        ]
    )
    tipo_comida = models.ManyToManyField(TipoComida, related_name='recetas')
    proteinas = models.IntegerField(validators=[MinValueValidator(0)])
    ingredientes = models.ManyToManyField(Ingrediente, related_name='recetas')
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='recetas')

    def __str__(self):
        return self.nombre
        
class Calendario(models.Model):
    fecha = models.DateField(unique=True)  # Cada día debe ser único
    objetivo_proteico = models.IntegerField(validators=[MinValueValidator(0)], default=100)
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='calendarios')

    def __str__(self):
        return f"Planificación del {self.fecha}"

    def calcular_proteinas_restantes(self):
        """Calcula cuántas proteínas faltan para alcanzar el objetivo diario."""
        proteinas_consumidas = sum(
            cr.receta.proteinas for cr in self.calendario_recetas.all()
        )
        return max(0, self.objetivo_proteico - proteinas_consumidas)

    @property
    def proteinas_consumidas(self):
        """Calcula las proteínas ya consumidas."""
        return sum(
            cr.receta.proteinas for cr in self.calendario_recetas.all()
        )
    def asignar_receta(self, receta, tipo_comida):
        """Asigna una receta a una fecha con su tipo de comida."""
        Calendario_Receta.objects.create(calendario=self, receta=receta, tipo_comida=tipo_comida)

    def eliminar_receta(self, receta, tipo_comida):
        """Elimina una receta específica de un tipo de comida en una fecha."""
        Calendario_Receta.objects.filter(calendario=self, receta=receta, tipo_comida=tipo_comida).delete()

class Calendario_Receta(models.Model):
    """Tabla intermedia que conecta Calendario con Receta y TipoComida."""
    calendario = models.ForeignKey(Calendario, on_delete=models.CASCADE, related_name="calendario_recetas")
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name="recetas_calendario")
    tipo_comida = models.ForeignKey(TipoComida, on_delete=models.CASCADE, related_name="tipo_comida_calendario")

    class Meta:
        unique_together = ("calendario", "receta", "tipo_comida")

    def __str__(self):
        return f"{self.receta} en {self.tipo_comida} el {self.calendario.fecha}"


class ListaCompra(models.Model):
    # Por ejemplo, para identificar a qué semana pertenece
    start_date = models.DateField(default=timezone.now)
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='listas_compra')

    # Si quieres enlazarlo a un usuario (aunque sea una app de un solo usuario),
    # podrías añadir un campo user = models.ForeignKey(User, on_delete=models.CASCADE)
    # si en el futuro quisieras multiusuario.

    def __str__(self):
        return f"Lista de la compra - Semana del {self.start_date}"

class ListaCompraItem(models.Model):
    """Representa un ingrediente en la lista, con las raciones originales, 
    cuántas faltan por comprar y cuántas tiene el usuario."""
    lista = models.ForeignKey(ListaCompra, on_delete=models.CASCADE, related_name="items")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE)
    original = models.PositiveIntegerField(default=0)
    compra = models.PositiveIntegerField(default=0)
    despensa = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('lista', 'ingrediente')
        
    def __str__(self):
        return f"{self.ingrediente.nombre} en {self.lista}"

