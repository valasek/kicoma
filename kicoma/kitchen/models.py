import datetime
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _


class VAT(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - DPH')
        verbose_name = _('číselník - DPH')

    percentage = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        unique=True, verbose_name='Výše', help_text='DPH procenta')
    name = models.CharField(max_length=100, unique=True, verbose_name='Sazba', help_text='DPH sazba')

    def __str__(self):
        return str(self.percentage) + '% - ' + self.name


class Allergen(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Alergény')
        verbose_name = _('číselník - Alergén')

    code = models.CharField(max_length=10, unique=True, verbose_name='Kód', help_text='Kód alergénu')
    description = models.CharField(max_length=150, unique=True, verbose_name='Název', help_text='Název alergénu')

    def __str__(self):
        return self.code + ' - ' + self.description


class Unit(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Jednotky')
        verbose_name = _('číselník - Jednotka')

    name = models.CharField(max_length=2, unique=True, verbose_name='Jednotka',
                            help_text='Objemová nebo váhová jednotka zboží')

    def __str__(self):
        return self.name


class TargetGroup(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Skupiny strávníků')
        verbose_name = _('číselník - Skupina strávníků')

    name = models.CharField(max_length=100, unique=True, verbose_name='Skupina strávníka',
                            help_text='Skupina pro kterou se připravuje jídlo')

    def __str__(self):
        return self.name


class MealType(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Druhy jídla')
        verbose_name = _('číselník - Druh jídla')

    name = models.CharField(max_length=30, unique=True, verbose_name='Druh jídla',
                            help_text='Druh jídla v rámci dne')
    category = models.CharField(max_length=30, verbose_name='Kategorie', help_text='Kategorie druhu jídla')

    def __str__(self):
        return self.name


class Article(models.Model):

    class Meta:
        verbose_name_plural = _('Zboží')
        verbose_name = _('Zboží')

    code = models.CharField(max_length=10, unique=True, verbose_name='Kód', help_text='Kód zboží')
    name = models.CharField(max_length=30, unique=True, verbose_name='Název zboží',
                            help_text='Název zboží na skladu')
    criticalAmount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        blank=True, null=True, verbose_name='Kritické množství', help_text='Minimální množství na skladu')
    averagePrice = models.DecimalField(
        max_digits=6, blank=True, null=True, decimal_places=2, verbose_name='Průměrná cena', help_text='Vypočtena průměrná cena zboží na jednotku')
    normPrice = models.DecimalField(
        max_digits=9, decimal_places=5, blank=True, null=True, verbose_name='Cena normy', help_text='Paní Trmalová doplní o čem je tahle položka')
    comment = models.TextField(max_length=200, blank=True, null=True, verbose_name='Poznámka')
    allergen = models.ManyToManyField(Allergen, blank=True, verbose_name='Alergény')

    def __str__(self):
        return self.name

    def display_allergens(self):
        '''Create a string for the Allergens. This is required to display allergen in Admin and user table view.'''
        return ', '.join(allergen.code for allergen in self.allergen.all())

    display_allergens.short_description = _('Alergény')

    def get_absolute_url(self):
        '''Returns the url to access a particular instance of the model.'''
        return reverse('model-detail-view', args=[str(self.id)])


class Recipe(models.Model):

    class Meta:
        verbose_name_plural = _('Recepty')
        verbose_name = _('Recept')

    name = models.CharField(max_length=100, unique=True, verbose_name='Jméno', help_text='Název receptu')
    norm_amount = models.PositiveSmallIntegerField(verbose_name='Normovaný počet', help_text='Počet porcí')
    comment = models.TextField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.name


class Ingredient(models.Model):

    class Meta:
        verbose_name_plural = _('Suroviny v receptu')
        verbose_name = _('Surovina v receptu')

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Surovina',
                                help_text='Použitá surovina')
    amount = models.DecimalField(
        decimal_places=2, max_digits=8,
        unique=True, verbose_name='Množství', help_text='Množství suroviny')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='Jednotka')

    def __str__(self):
        return self.recipe.name + '-  ' + self.article.name + '-  ' + str(self.amount) + 'x'


class DailyMenu(models.Model):

    class Meta:
        verbose_name_plural = _('Denní jídla')
        verbose_name = _('Denní jídlo')

    date = models.DateField(verbose_name='Datum')
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        unique=True, verbose_name='Počet', help_text='Počet porcí')
    targetGroup = models.ForeignKey(TargetGroup, on_delete=models.CASCADE, verbose_name='Skupina strávníka',
                                    help_text='Skupina pro kterou se připravuje jídlo')
    mealType = models.ForeignKey(MealType, on_delete=models.CASCADE, verbose_name='Druh jídla',
                                 help_text='Druh jídla v rámci dne')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept',
                               help_text='Vybraný recept')

    def __str__(self):
        return str(self.date) + ' - ' + self.mealType.name + ' - ' + str(self.amount) + 'x - ' + self.targetGroup.name


class StockIssue(models.Model):

    class Meta:
        verbose_name_plural = _('Výdejky')
        verbose_name = _('Výdejka')

    createdAt = models.DateField(verbose_name='Datum vytvoření')
    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='created', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Odepsáno ze skladu')
    approvedDate = models.DateField(blank=True, null=True, verbose_name='Datum odpisu ze skladu')
    userApproved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='approved', verbose_name='Odepsal ze skladu')
    dailyMenu = models.ForeignKey(DailyMenu, on_delete=models.CASCADE, blank=True,
                                  null=True, verbose_name='Vydáno v menu')
    comment = models.TextField(max_length=200, blank=True, null=True, verbose_name='Poznámka')


class StockReceipt(models.Model):

    class Meta:
        verbose_name_plural = _('Příjemky')
        verbose_name = _('Příjemka')

    createdAt = models.DateField(default=datetime.date.today ,verbose_name='Datum vytvoření')
    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='received', verbose_name='Přijal')
    comment = models.TextField(max_length=200, blank=True, null=True, verbose_name='Poznámka')


class Item(models.Model):

    class Meta:
        verbose_name_plural = _('Skladové položky')
        verbose_name = _('Skladová položka')

    stockReceipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, verbose_name='Příjemka')
    stockIssue = models.ForeignKey(StockIssue, on_delete=models.CASCADE, verbose_name='Výdejka')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží')
    amount = models.DecimalField(
        decimal_places=2, max_digits=8,
        unique=True, verbose_name='Množství', help_text='Množství suroviny')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='Jednotka')
    priceWithoutVat = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Cena bez DPH')
    priceWithVat = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name='Vypočtena cena s DPH')
    comment = models.TextField(max_length=200, verbose_name='Poznámka')

    def __str__(self):
        return self.article.name + ' - ' + self.amount + self.unit.name

    def get_absolute_url(self):
        '''Returns the url to access a particular instance of the model.'''
        return reverse('kicoma.Item.update', args=[str(self.id)])
