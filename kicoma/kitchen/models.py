# import datetime
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.forms import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from .functions import convertUnits

UNIT = (
    ('kg', _('kilogram')),
    ('g', _('gram')),
    ('l', _('litr')),
    ('ml', _('mililitr')),
    ('ks', _('kus')),
)


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name='Datum vytvoření')
    modified = models.DateTimeField(auto_now=True, verbose_name='Datum aktualizace')

    class Meta:
        abstract = True


class VAT(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - DPH')
        verbose_name = _('číselník - DPH')

    percentage = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        unique=True, verbose_name='Výše', help_text='DPH procenta')
    rate = models.CharField(max_length=100, unique=True, verbose_name='Sazba', help_text='DPH sazba')

    def __str__(self):
        return str(self.percentage) + '%'


class Allergen(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Alergény')
        verbose_name = _('číselník - Alergén')

    code = models.CharField(max_length=10, unique=True, verbose_name='Kód', help_text='Kód alergénu')
    description = models.CharField(max_length=150, unique=True, verbose_name='Název', help_text='Název alergénu')

    def __str__(self):
        return self.code + ' - ' + self.description


class MealGroup(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Skupiny strávníků')
        verbose_name = _('číselník - Skupina strávníků')

    mealGroup = models.CharField(max_length=100, unique=True, verbose_name='Skupina strávníka',
                                 help_text='Skupina pro kterou se připravuje jídlo')

    def __str__(self):
        return self.mealGroup


class MealType(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Druhy jídla')
        verbose_name = _('číselník - Druh jídla')

    mealType = models.CharField(max_length=30, unique=True, verbose_name='Druh jídla',
                                help_text='Druh jídla v rámci dne')

    def __str__(self):
        return self.mealType


class Article(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Zboží')
        verbose_name = _('Zboží')
        ordering = ['article']

    article = models.CharField(max_length=30, unique=True, verbose_name='Zboží',
                               help_text='Název zboží na skladu')
    onStock = models.DecimalField(
        decimal_places=2, max_digits=8,
        default=0, verbose_name='Na skladu', help_text='Celkové množství zboží na skladu')
    totalPrice = models.DecimalField(
        max_digits=8, blank=True, null=True, decimal_places=2,
        default=0, verbose_name='Celková cena', help_text='Celková cena zboží na skladu')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    comment = models.TextField(max_length=200, blank=True, null=True, verbose_name='Poznámka')
    allergen = models.ManyToManyField(Allergen, blank=True, verbose_name='Alergény')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.article

    @property
    def averagePrice(self):
        if self.onStock != 0:
            return self.totalPrice / self.onStock
        else:
            return 0
    # display_averagePrice.short_description = _('Průměrná jednotková cena')
    # verbose_name='', help_text='Průměrná cena na jednotku zboží')

    def display_allergens(self):
        '''Create a string for the Allergens. This is required to display allergen in Admin and user table view.'''
        return ', '.join(allergen.code for allergen in self.allergen.all())
    display_allergens.short_description = _('Alergény')

    def get_absolute_url(self):
        '''Returns the url to access a particular instance of the model.'''
        return reverse('model-detail-view', args=[str(self.id)])


class Recipe(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Recepty')
        verbose_name = _('Recept')
        ordering = ['recipe']

    recipe = models.CharField(max_length=100, unique=True, verbose_name='recept', help_text='Název receptu')
    norm_amount = models.PositiveSmallIntegerField(verbose_name='Počet porcí')
    procedure = models.TextField(max_length=200, blank=True, null=True, verbose_name='Postup')

    def __str__(self):
        return self.recipe


class Ingredient(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Suroviny v receptu')
        verbose_name = _('Surovina v receptu')
        ordering = ['-recipe__recipe']

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Surovina',
                                help_text='Použitá surovina')
    amount = models.DecimalField(
        decimal_places=2, max_digits=10,
        verbose_name='Množství', help_text='Množství suroviny')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')

    def __str__(self):
        return self.recipe.recipe + '-  ' + self.article.article + '-  ' + str(self.amount)


class DailyMenu(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Denní jídla')
        verbose_name = _('Denní jídlo')
        ordering = ['-date']

    date = models.DateField(verbose_name='Datum')
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        unique=True, verbose_name='Počet', help_text='Počet porcí')
    mealGroup = models.ForeignKey(MealGroup, on_delete=models.CASCADE, verbose_name='Skupina strávníka',
                                  help_text='Skupina pro kterou se připravuje jídlo')
    mealType = models.ForeignKey(MealType, on_delete=models.CASCADE, verbose_name='Druh jídla',
                                 help_text='Druh jídla v rámci dne')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept',
                               help_text='Vybraný recept')

    def __str__(self):
        return str(self.date) + ' - ' + self.mealType.mealType + ' - ' + str(self.amount) + ' - ' + self.mealGroup.mealGroup


class StockIssue(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Výdejky')
        verbose_name = _('Výdejka')
        ordering = ['-created']

    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='created', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Odepsáno ze skladu')
    dateApproved = models.DateField(blank=True, null=True, verbose_name='Datum odpisu ze skladu')
    userApproved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='approved', verbose_name='Odepsal ze skladu')
    dailyMenu = models.ForeignKey(DailyMenu, on_delete=models.CASCADE, blank=True,
                                  null=True, verbose_name='Vydáno v menu')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)


class StockReceipt(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Příjemky')
        verbose_name = _('Příjemka')
        ordering = ['-created']

    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='received', verbose_name='Přijal')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)

    def get_absolute_url(self):
        '''Returns the url to access a particular instance of the model.'''
        return reverse('kicoma.update', args=[str(self.id)])


class Item(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Položky')
        verbose_name = _('Položka')
        ordering = ['-article__article']

    stockReceipt = models.ForeignKey(StockReceipt, blank=True, null=True, on_delete=models.CASCADE,
                                     verbose_name='Příjemka')
    stockIssue = models.ForeignKey(StockIssue, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Výdejka')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží')
    amount = models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Množství')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    priceWithoutVat = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Cena bez DPH')
    vat = models.ForeignKey(VAT, blank=True, null=True, default=1, on_delete=models.CASCADE, verbose_name='DPH')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    @property
    def price_with_vat(self):
        return self.priceWithoutVat + self.priceWithoutVat * self.vat.percentage/100

    def clean(self):
        article = Article.objects.filter(pk=self.article.id).values_list('onStock', 'unit')
        onStock = article[0][0]
        stockUnit = article[0][1]
        issuedAmount = convertUnits(self.amount, self.unit, stockUnit)
        if self.stockIssue is not None and (onStock - issuedAmount < 0):
            raise ValidationError(
                {'amount': _("Na skladu je {0} {1} a vydáváte {2} {1}.".format(onStock, stockUnit, issuedAmount))})
        if self.stockReceipt is not None and (self.priceWithoutVat is None):
            raise ValidationError(
                {'priceWithoutVat': _("Uveď cenu.")})
        if self.stockReceipt is not None and (self.vat is None):
            raise ValidationError(
                {'vat': _("Uveď DPH.")})

    def __str__(self):
        return self.article.article + ' - ' + str(self.amount) + self.unit

    def get_absolute_url(self):
        '''Returns the url to access a particular instance of the model.'''
        return reverse('kicoma.Item.update', args=[str(self.id)])
