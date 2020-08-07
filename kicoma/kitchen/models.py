from decimal import Decimal

from django.db import models
from django.conf import settings
from django.forms import ValidationError
from django.contrib import messages
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from .functions import convertUnits, totalItemPrice


def updateArticleStock(stock_id, stock_direction):
    if stock_direction == 'receipt':
        items = Item.objects.filter(stockReceipt=stock_id)
    else:
        if stock_direction == 'issue':
            items = Item.objects.filter(stockIssue=stock_id)
        else:
            raise Exception(
                "Item is not linked to StockReceipt or StockIssue or linked to both. Only one should be populated.")
    for item in items:
        article = Article.objects.filter(pk=item.article.id).values_list('onStock', 'totalPrice', 'unit').get()
        on_stock = article[0]
        total_price = article[1]
        article_unit = article[2]
        if stock_direction == 'receipt':
            Article.objects.filter(pk=item.article_id).update(
                onStock=on_stock + convertUnits(item.amount, item.unit, article_unit),
                totalPrice=total_price + convertUnits(item.price_with_vat, article_unit, item.unit))
            print(stock_direction, item.article, item.article.id,
                  "mnozství: ", on_stock, "+", convertUnits(item.amount, item.unit, article_unit),
                  "cena: ", total_price, "+", convertUnits(item.price_with_vat, article_unit, item.unit))
            return None
        if stock_direction == 'issue':
            average_price = convertUnits(item.article.averagePrice, article_unit, item.unit)
            converted_amount = convertUnits(item.amount, item.unit, article_unit)
            if on_stock < 0 or on_stock - converted_amount < 0:
                print(on_stock, converted_amount)
                return "Není možné vyskladnit zboží {}, vyskladňuješ {} a na skladu je jenom {}".format(
                    item.article, converted_amount, on_stock)
            Article.objects.filter(pk=item.article_id).update(
                onStock=on_stock - converted_amount,
                totalPrice=total_price - average_price)
            print(stock_direction, item.article, item.article.id,
                  "mnozství: ", on_stock, "-", convertUnits(item.amount, item.unit, article_unit),
                  "cena: ", total_price, "-", convertUnits(item.article.averagePrice, article_unit, item.unit))
            return None


UNIT = (
    ('kg', _('kg')),
    ('g', _('g')),
    ('l', _('l')),
    ('ml', _('ml')),
    ('ks', _('ks')),
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
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    onStock = models.DecimalField(
        decimal_places=2, max_digits=8,
        default=0, verbose_name='Na skladu', help_text='Celkové množství zboží na skladu')
    minOnStock = models.DecimalField(
        decimal_places=2, max_digits=8, validators=[MinValueValidator(Decimal('0.1'))],
        default=0, verbose_name='Minimálně na skladu', help_text='Minimální množství zboží na skladu')
    totalPrice = models.DecimalField(
        max_digits=8, blank=True, null=True, decimal_places=2,
        default=0, verbose_name='Celková cena', help_text='Celková cena zboží na skladu')
    allergen = models.ManyToManyField(Allergen, blank=True, verbose_name='Alergény')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.article

    @property
    def averagePrice(self):
        if self.onStock != 0:
            return round(self.totalPrice / self.onStock, 2)
        return 0

    def display_allergens(self):
        '''Create a string for the Allergens. This is required to display allergen in Admin and user table view.'''
        return ', '.join(allergen.code for allergen in self.allergen.all())
    display_allergens.short_description = _('Alergény')


class Recipe(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Recepty')
        verbose_name = _('Recept')
        ordering = ['recipe']

    recipe = models.CharField(max_length=100, unique=True, verbose_name='recept', help_text='Název receptu')
    norm_amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)], verbose_name='Počet porcí')
    procedure = models.TextField(max_length=1000, blank=True, null=True, verbose_name='Postup receptu')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe

    @property
    def recipePrice(self):
        ingredients = Ingredient.objects.filter(recipe=self.id)
        return round(totalItemPrice(ingredients), 2)


class Ingredient(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Suroviny v receptu')
        verbose_name = _('Surovina v receptu')
        ordering = ['-recipe']

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Surovina',
                                help_text='Použitá surovina')
    amount = models.DecimalField(
        decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.1'))],
        verbose_name='Množství', help_text='Množství suroviny')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe.recipe + '-  ' + self.article.article + '-  ' + str(self.amount)


class DailyMenu(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Denní jídla')
        verbose_name = _('Denní jídlo')
        ordering = ['-date']

    date = models.DateField(verbose_name='Datum', help_text='Datum denního menu ve formátu dd.mm.rrrr')
    mealGroup = models.ForeignKey(MealGroup, on_delete=models.CASCADE, verbose_name='Skupina strávníka',
                                  help_text='Skupina pro kterou se připravuje jídlo')
    mealType = models.ForeignKey(MealType, on_delete=models.CASCADE, verbose_name='Druh jídla',
                                 help_text='Druh jídla v rámci dne')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.date) + ' - ' + self.mealType.mealType + ' - ' + self.mealGroup.mealGroup


class DailyMenuRecipe(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Recepty denního menu')
        verbose_name = _('Recepty denního menu')
        ordering = ['-recipe']

    daily_menu = models.ForeignKey(DailyMenu, on_delete=models.CASCADE, verbose_name='Denní menu')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept',
                               help_text='Vybraný recept')
    amount = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(1000)],
                                              verbose_name='Počet', help_text='Počet porcí')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe.recipe + ' - ' + str(self.amount)


class StockIssue(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Výdejky')
        verbose_name = _('Výdejka')
        ordering = ['-created']

    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='usicreated', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Vyskladněno')
    dateApproved = models.DateField(blank=True, null=True, verbose_name='Datum vyskladnění')
    userApproved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='usiapproved', verbose_name='Vyskladnil')
    # dailyMenu = models.ForeignKey(DailyMenu, on_delete=models.CASCADE, blank=True,
    #                               null=True, verbose_name='Vydáno v menu')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        items = Item.objects.filter(stockIssue=self.id)
        return round(totalItemPrice(items), 2)


class StockReceipt(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Příjemky')
        verbose_name = _('Příjemka')
        ordering = ['-created']

    userCreated = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='usrcreated', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Naskladněno')
    dateApproved = models.DateField(blank=True, null=True, verbose_name='Datum naskladnění')
    userApproved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='usrapproved', verbose_name='Naskladnil')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        items = Item.objects.filter(stockReceipt=self.id)
        return round(totalItemPrice(items), 2)


class Item(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Zboží')
        verbose_name = _('Zboží')
        ordering = ['-article__article']

    stockReceipt = models.ForeignKey(StockReceipt, blank=True, null=True, on_delete=models.CASCADE,
                                     verbose_name='Příjemka')
    stockIssue = models.ForeignKey(StockIssue, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Výdejka')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží')
    amount = models.DecimalField(decimal_places=2, max_digits=8, validators=[
                                 MinValueValidator(Decimal('0.1'))], verbose_name='Množství')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    priceWithoutVat = models.DecimalField(max_digits=10, decimal_places=2, validators=[
        MinValueValidator(Decimal('0.1'))], blank=True, null=True, verbose_name='Jednotková cena bez DPH')
    vat = models.ForeignKey(VAT, blank=True, null=True, default=2, on_delete=models.CASCADE, verbose_name='DPH')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    @property
    def price_with_vat(self):
        if self.priceWithoutVat is not None and self.priceWithoutVat is not None and self.vat.percentage is not None:
            return self.priceWithoutVat + self.priceWithoutVat * self.vat.percentage/100
        return 0  # Required for Items on StockIssues

    @property
    def total_price_with_vat(self):
        if self.price_with_vat is not None and self.amount is not None:
            return round(self.price_with_vat * self.amount, 2)
        return 0  # Required for Items on StockIssues

    @property
    def total_average_price_with_vat(self):
        if self.amount is not None and self.article.averagePrice is not None:
            return round(self.amount * self.article.averagePrice, 2)
        return 0  # Required for Items on StockIssues

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
