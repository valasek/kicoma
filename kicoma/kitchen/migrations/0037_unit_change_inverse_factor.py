from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kitchen", "0036_unit_change_log"),
    ]


    operations = [
        migrations.AlterField(
            model_name="unitchangelog",
            name="factor",
            field=models.DecimalField(
                max_digits=13,
                decimal_places=6,
                verbose_name="Převodní koeficient",
            ),
        ),
    ]
