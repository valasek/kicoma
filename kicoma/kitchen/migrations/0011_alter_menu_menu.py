# Generated by Django 3.2.10 on 2022-02-20 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0010_menu_menurecipe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='menu',
            name='menu',
            field=models.CharField(help_text='Název menu', max_length=100, unique=True, verbose_name='menu'),
        ),
    ]
