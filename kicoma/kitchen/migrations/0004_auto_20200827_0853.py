# Generated by Django 3.1 on 2020-08-27 06:53

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0003_auto_20200824_1036'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dailymenu',
            options={'ordering': ['-date', 'meal_group'], 'verbose_name': 'Denní menu', 'verbose_name_plural': 'Denní menu'},
        ),
        migrations.AlterField(
            model_name='stockissuearticle',
            name='average_unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.1'))], verbose_name='Průměrná jednotková cena s DPH'),
        ),
    ]
