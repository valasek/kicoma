# Generated by Django 3.2.10 on 2022-02-20 19:00

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0009_auto_20220215_1719'),
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('menu', models.CharField(help_text='Menu', max_length=100, unique=True, verbose_name='menu')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('meal_type', models.ForeignKey(help_text='Druh jídla v rámci dne', on_delete=django.db.models.deletion.CASCADE, to='kitchen.mealtype', verbose_name='Druh jídla')),
            ],
            options={
                'verbose_name': 'Menu',
                'verbose_name_plural': 'Menu',
                'ordering': ['meal_type'],
            },
        ),
        migrations.CreateModel(
            name='MenuRecipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('amount', models.PositiveSmallIntegerField(help_text='Počet porcí', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1000)], verbose_name='Porcí')),
                ('menu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kitchen.menu', verbose_name='Menu')),
                ('recipe', models.ForeignKey(help_text='Vybraný recept', on_delete=django.db.models.deletion.CASCADE, to='kitchen.recipe', verbose_name='Recept')),
            ],
            options={
                'verbose_name': 'Recepty menu',
                'verbose_name_plural': 'Recepty menu',
                'ordering': ['menu', 'recipe', 'amount'],
            },
        ),
    ]
