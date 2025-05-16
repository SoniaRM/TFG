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
                regex=r'^[a-zA-Z]+$',  
                message='El nombre solo puede contener letras.',
                code='invalid_nombre'
            )
        ], 
        unique=True)

    def __str__(self):
        return self.nombre

class Familia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo_invitacion = models.CharField(max_length=8, unique=True, blank=True)
    miembros = models.ManyToManyField(User, related_name='familias')
    administrador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_familias'
    )

    def save(self, *args, **kwargs):
        if not self.codigo_invitacion:
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
        self.recetas.all().delete()
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
    carbohidratos = models.IntegerField(validators=[MinValueValidator(0)])
    ingredientes = models.ManyToManyField(Ingrediente, related_name='recetas')
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='recetas')
    descripcion = models.TextField(
        verbose_name="Descripción",
        blank=True,
        null=True,
        help_text="Descripción de la receta (opcional)."
    )
    combinable = models.BooleanField(
        default=True,
        help_text="Indica si la receta puede combinarse con otras."
    )

    def __str__(self):
        return self.nombre
        
class Calendario(models.Model):
    fecha = models.DateField()
    objetivo_proteico = models.IntegerField(validators=[MinValueValidator(0)], default=100)
    objetivo_carbohidratos = models.IntegerField(validators=[MinValueValidator(0)], default=250)

    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='calendarios')

    class Meta:
        unique_together = ('familia', 'fecha') 

    def __str__(self):
        return f"Planificación del {self.fecha} para {self.familia}"

    def calcular_proteinas_restantes(self):
        """Calcula cuántas proteínas faltan para alcanzar el objetivo diario."""
        proteinas_consumidas = sum(
            cr.receta.proteinas for cr in self.calendario_recetas.all()
        )
        return max(0, self.objetivo_proteico - proteinas_consumidas)

    def calcular_carbos_restantes(self):
        """Calcula cuántos carbos faltan para alcanzar el objetivo diario."""
        carbos_consumidos = sum(
            cr.receta.carbohidratos for cr in self.calendario_recetas.all()
        )
        return max(0, self.objetivo_carbohidratos - carbos_consumidos)

    @property
    def proteinas_consumidas(self):
        """Calcula las proteínas ya consumidas."""
        return sum(
            cr.receta.proteinas for cr in self.calendario_recetas.all()
        )

    @property
    def carbohidratos_consumidos(self):
        """Calcula los carbohidratos ya consumidos."""
        return sum(
            cr.receta.carbohidratos for cr in self.calendario_recetas.all()
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
    start_date = models.DateField(default=timezone.now)
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='listas_compra')

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


class SolicitudUniónFamilia(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_familia')
    familia = models.ForeignKey('Familia', on_delete=models.CASCADE, related_name='solicitudes')
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solicitud de {self.usuario.username} a {self.familia.nombre} ({self.estado})"
