from django.db import models


class MealType(models.Model):

    class Meta:
        verbose_name_plural = "Druhy jídla"
        ordering = ['name']

    name = models.CharField(max_length=100, verbose_name="Název")
    category = models.CharField(max_length=100, verbose_name="Kategorie")

    def __str__(self):
        return self.name + ", " + self.category


class TargetGroup(models.Model):

    class Meta:
        verbose_name_plural = "Skupiny strávníků"
        ordering = ['name']

    name = models.CharField(max_length=100, verbose_name="Skupina strávníka")

    def __str__(self):
        return self.name

# ToDo - pojit s ingrediencema


class Allergen(models.Model):

    class Meta:
        verbose_name_plural = "Alergeny"
        ordering = ['code']

    code = models.CharField(max_length=100, verbose_name="Skratka")
    description = models.CharField(max_length=100, verbose_name="Název")

    def __str__(self):
        return self.code + ' - ' + self.description


class Unit(models.Model):

    class Meta:
        verbose_name_plural = "Jednotky"
        ordering = ['name']

    name = models.CharField(max_length=2, verbose_name="Jednotka")

    def __str__(self):
        return self.name


class RecipeBook(models.Model):

    class Meta:
        verbose_name_plural = "Receptář"
        ordering = ['code']

    code = models.CharField(max_length=6, unique=True, verbose_name="Kód")
    name = models.CharField(max_length=100, verbose_name="Jméno")
    norm_amount = models.PositiveSmallIntegerField(
        verbose_name="Normovaný počet")

    def __str__(self):
        return self.code + " - " + self.name + ", " + str(self.norm_amount)


class Item(models.Model):

    class Meta:
        verbose_name_plural = "Skladové položky"
        ordering = ['code']

    code = models.CharField(max_length=6, unique=True, verbose_name="Kód")
    name = models.CharField(max_length=100, verbose_name="Název ingredence")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    allergen = models.ManyToManyField(Allergen, blank=True)
    coefficient = models.DecimalField(
        max_digits=5, decimal_places=4, default=1, verbose_name="Koeficient")
    in_stock = models.DecimalField(
        max_digits=6, decimal_places=3, default=0, verbose_name="Skladem")
    price = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Cena")
    cena_normy = models.DecimalField(
        max_digits=9, decimal_places=5, blank=True, null=True)

    def __str__(self):
        return self.code + " - " + self.name
