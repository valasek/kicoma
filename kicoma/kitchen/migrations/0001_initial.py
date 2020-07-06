# Generated by Django 3.0.8 on 2020-07-06 19:23

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Allergen',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='Kód alergénu', max_length=10, unique=True, verbose_name='Kód')),
                ('description', models.CharField(help_text='Název alergénu', max_length=150, unique=True, verbose_name='Název')),
            ],
            options={
                'verbose_name': 'číselník - Alergén',
                'verbose_name_plural': 'číselník - Alergény',
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('article', models.CharField(help_text='Název zboží na skladu', max_length=30, unique=True, verbose_name='Zboží')),
                ('unit', models.CharField(choices=[('kg', 'kg'), ('g', 'g'), ('l', 'l'), ('ml', 'ml'), ('ks', 'ks')], max_length=2, verbose_name='Jednotka')),
                ('onStock', models.DecimalField(decimal_places=2, default=0, help_text='Celkové množství zboží na skladu', max_digits=8, verbose_name='Na skladu')),
                ('minOnStock', models.DecimalField(decimal_places=2, default=0, help_text='Minimální množství zboží na skladu', max_digits=8, verbose_name='Minimálně na skladu')),
                ('totalPrice', models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Celková cena zboží na skladu', max_digits=8, null=True, verbose_name='Celková cena')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('allergen', models.ManyToManyField(blank=True, to='kitchen.Allergen', verbose_name='Alergény')),
            ],
            options={
                'verbose_name': 'Zboží',
                'verbose_name_plural': 'Zboží',
                'ordering': ['article'],
            },
        ),
        migrations.CreateModel(
            name='DailyMenu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('date', models.DateField(help_text='Datum denního menu', verbose_name='Datum')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
            ],
            options={
                'verbose_name': 'Denní jídlo',
                'verbose_name_plural': 'Denní jídla',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='MealGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mealGroup', models.CharField(help_text='Skupina pro kterou se připravuje jídlo', max_length=100, unique=True, verbose_name='Skupina strávníka')),
            ],
            options={
                'verbose_name': 'číselník - Skupina strávníků',
                'verbose_name_plural': 'číselník - Skupiny strávníků',
            },
        ),
        migrations.CreateModel(
            name='MealType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mealType', models.CharField(help_text='Druh jídla v rámci dne', max_length=30, unique=True, verbose_name='Druh jídla')),
            ],
            options={
                'verbose_name': 'číselník - Druh jídla',
                'verbose_name_plural': 'číselník - Druhy jídla',
            },
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('recipe', models.CharField(help_text='Název receptu', max_length=100, unique=True, verbose_name='recept')),
                ('norm_amount', models.PositiveSmallIntegerField(verbose_name='Počet porcí')),
                ('procedure', models.TextField(blank=True, max_length=200, null=True, verbose_name='Postup receptu')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
            ],
            options={
                'verbose_name': 'Recept',
                'verbose_name_plural': 'Recepty',
                'ordering': ['recipe'],
            },
        ),
        migrations.CreateModel(
            name='VAT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentage', models.PositiveSmallIntegerField(help_text='DPH procenta', unique=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Výše')),
                ('rate', models.CharField(help_text='DPH sazba', max_length=100, unique=True, verbose_name='Sazba')),
            ],
            options={
                'verbose_name': 'číselník - DPH',
                'verbose_name_plural': 'číselník - DPH',
            },
        ),
        migrations.CreateModel(
            name='StockReceipt',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('userCreated', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received', to=settings.AUTH_USER_MODEL, verbose_name='Přijal')),
            ],
            options={
                'verbose_name': 'Příjemka',
                'verbose_name_plural': 'Příjemky',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='StockIssue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('approved', models.BooleanField(blank=True, default=False, null=True, verbose_name='Vyskladněno')),
                ('dateApproved', models.DateField(blank=True, null=True, verbose_name='Datum odpisu')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('userApproved', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='uapproved', to=settings.AUTH_USER_MODEL, verbose_name='Vyskladnil')),
                ('userCreated', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ucreated', to=settings.AUTH_USER_MODEL, verbose_name='Vytvořil')),
            ],
            options={
                'verbose_name': 'Výdejka',
                'verbose_name_plural': 'Výdejky',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Množství')),
                ('unit', models.CharField(choices=[('kg', 'kg'), ('g', 'g'), ('l', 'l'), ('ml', 'ml'), ('ks', 'ks')], max_length=2, verbose_name='Jednotka')),
                ('priceWithoutVat', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Cena bez DPH')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kitchen.Article', verbose_name='Zboží')),
                ('stockIssue', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='kitchen.StockIssue', verbose_name='Výdejka')),
                ('stockReceipt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='kitchen.StockReceipt', verbose_name='Příjemka')),
                ('vat', models.ForeignKey(blank=True, default=1, null=True, on_delete=django.db.models.deletion.CASCADE, to='kitchen.VAT', verbose_name='DPH')),
            ],
            options={
                'verbose_name': 'Zboží',
                'verbose_name_plural': 'Zboží',
                'ordering': ['-article__article'],
            },
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Množství suroviny', max_digits=10, verbose_name='Množství')),
                ('unit', models.CharField(choices=[('kg', 'kg'), ('g', 'g'), ('l', 'l'), ('ml', 'ml'), ('ks', 'ks')], max_length=2, verbose_name='Jednotka')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('article', models.ForeignKey(help_text='Použitá surovina', on_delete=django.db.models.deletion.CASCADE, to='kitchen.Article', verbose_name='Surovina')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kitchen.Recipe', verbose_name='Recept')),
            ],
            options={
                'verbose_name': 'Surovina v receptu',
                'verbose_name_plural': 'Suroviny v receptu',
                'ordering': ['-recipe'],
            },
        ),
        migrations.CreateModel(
            name='DailyMenuRecipe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')),
                ('amount', models.PositiveSmallIntegerField(help_text='Počet porcí', unique=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1000)], verbose_name='Počet')),
                ('comment', models.CharField(blank=True, max_length=200, null=True, verbose_name='Poznámka')),
                ('daily_menu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kitchen.DailyMenu', verbose_name='Denní menu')),
                ('recipe', models.ForeignKey(help_text='Vybraný recept', on_delete=django.db.models.deletion.CASCADE, to='kitchen.Recipe', verbose_name='Recept')),
            ],
            options={
                'verbose_name': 'Recepty denního menu',
                'verbose_name_plural': 'Recepty denního menu',
                'ordering': ['-recipe'],
            },
        ),
        migrations.AddField(
            model_name='dailymenu',
            name='mealGroup',
            field=models.ForeignKey(help_text='Skupina pro kterou se připravuje jídlo', on_delete=django.db.models.deletion.CASCADE, to='kitchen.MealGroup', verbose_name='Skupina strávníka'),
        ),
        migrations.AddField(
            model_name='dailymenu',
            name='mealType',
            field=models.ForeignKey(help_text='Druh jídla v rámci dne', on_delete=django.db.models.deletion.CASCADE, to='kitchen.MealType', verbose_name='Druh jídla'),
        ),
    ]
