# Generated by Django 5.1.1 on 2025-03-05 12:12

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_alter_ingrediente_nombre_alter_receta_nombre'),
    ]

    operations = [
        migrations.CreateModel(
            name='Calendario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(unique=True)),
                ('objetivo_proteico', models.IntegerField(default=100, validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.CreateModel(
            name='Calendario_Receta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calendario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calendario_recetas', to='app.calendario')),
                ('receta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recetas_calendario', to='app.receta')),
                ('tipo_comida', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tipo_comida_calendario', to='app.tipocomida')),
            ],
            options={
                'unique_together': {('calendario', 'receta', 'tipo_comida')},
            },
        ),
    ]
