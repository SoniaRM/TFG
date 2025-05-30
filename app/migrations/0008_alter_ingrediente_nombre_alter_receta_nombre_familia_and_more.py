# Generated by Django 5.1.1 on 2025-04-10 06:58

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_listacompraitem_unique_together'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingrediente',
            name='nombre',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator(code='invalid_nombre', message='El nombre solo puede contener letras, números, espacios, comas y la letra ñ.', regex='^[a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ,\\s]+$')]),
        ),
        migrations.AlterField(
            model_name='receta',
            name='nombre',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator(code='invalid_nombre', message='El nombre solo puede contener letras, números, espacios, comas y la letra ñ.', regex='^[a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ,\\s]+$')]),
        ),
        migrations.CreateModel(
            name='Familia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('miembros', models.ManyToManyField(related_name='familias', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='calendario',
            name='familia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendarios', to='app.familia'),
        ),
        migrations.AddField(
            model_name='ingrediente',
            name='familia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ingredientes', to='app.familia'),
        ),
        migrations.AddField(
            model_name='listacompra',
            name='familia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='listas_compra', to='app.familia'),
        ),
        migrations.AddField(
            model_name='receta',
            name='familia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recetas', to='app.familia'),
        ),
    ]
