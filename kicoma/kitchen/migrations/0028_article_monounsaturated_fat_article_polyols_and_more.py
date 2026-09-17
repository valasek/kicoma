import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0027_alter_article_carbohydrates_alter_article_energy_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='monounsaturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho mononenasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='article',
            name='polyols',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho polyoly'),
        ),
        migrations.AddField(
            model_name='article',
            name='polyunsaturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho polynenasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='article',
            name='salt',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='Sůl'),
        ),
        migrations.AddField(
            model_name='article',
            name='saturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho nasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='article',
            name='starch',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho škrob'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='monounsaturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho mononenasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='polyols',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho polyoly'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='polyunsaturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho polynenasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='salt',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='Sůl'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='saturated_fat',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho nasycené mastné kyseliny'),
        ),
        migrations.AddField(
            model_name='historicalarticle',
            name='starch',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho škrob'),
        ),
        migrations.AlterField(
            model_name='article',
            name='sugars',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho cukry'),
        ),
        migrations.AlterField(
            model_name='historicalarticle',
            name='sugars',
            field=models.DecimalField(blank=True, decimal_places=1, default=0, help_text='g / 100 g', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='z toho cukry'),
        ),
    ]
