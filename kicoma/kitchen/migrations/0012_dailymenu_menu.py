# Generated by Django 3.2.10 on 2022-02-24 07:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0011_alter_menu_menu'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailymenu',
            name='menu',
            field=models.ForeignKey(blank=True, help_text='Přeber recepty z připraveného menu', null=True, on_delete=django.db.models.deletion.CASCADE, to='kitchen.menu', verbose_name='Menu'),
        ),
    ]
