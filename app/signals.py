from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import TipoComida

@receiver(post_migrate)
def crear_tipos_comida(sender, **kwargs):
    if sender.name == "app":  # Solo afecta a la app 'recetas'
        tipos = ["Desayuno", "Almuerzo", "Merienda", "Cena"]
        for tipo in tipos:
            TipoComida.objects.get_or_create(nombre=tipo)
