# Generated by Django 3.1.3 on 2020-11-19 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0006_auto_20200906_1254'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dailymenurecipe',
            options={'ordering': ['recipe'], 'verbose_name': 'Recepty denního menu', 'verbose_name_plural': 'Recepty denního menu'},
        ),
    ]