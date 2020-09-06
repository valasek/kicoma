from decimal import Decimal
import datetime

from django.db import models, transaction
from django.db.models import Sum, Count, Min
from django.urls import reverse_lazy
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from simple_history.models import HistoricalRecords
from simple_history.utils import update_change_reason

from .functions import convertUnits, totalRecipeArticlePrice

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

    meal_group = models.CharField(max_length=100, unique=True, verbose_name='Skupina strávníka',
                                  help_text='Skupina pro kterou se připravuje jídlo')

    def __str__(self):
        return self.meal_group


class MealType(models.Model):

    class Meta:
        verbose_name_plural = _('číselník - Druhy jídla')
        verbose_name = _('číselník - Druh jídla')

    meal_type = models.CharField(max_length=30, unique=True, verbose_name='Druh jídla',
                                 help_text='Druh jídla v rámci dne')

    def __str__(self):
        return self.meal_type


class Article(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Zboží')
        verbose_name = _('Zboží')
        ordering = ['article']

    article = models.CharField(max_length=30, unique=True, verbose_name='Zboží',
                               help_text='Název zboží na skladu')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    on_stock = models.DecimalField(
        decimal_places=2, max_digits=8,
        default=0, verbose_name='Na skladu', help_text='Celkové množství zboží na skladu')
    min_on_stock = models.DecimalField(
        decimal_places=2, max_digits=8, blank=True, validators=[MinValueValidator(Decimal('0'))],
        default=0, verbose_name='Minimálně na skladu', help_text='Minimální množství zboží na skladu')
    total_price = models.DecimalField(
        max_digits=8, blank=True, null=True, decimal_places=2,
        default=0, verbose_name='Celková cena s DPH', help_text='Celková cena zboží na skladu')
    allergen = models.ManyToManyField(Allergen, blank=True, verbose_name='Alergény')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return self.article

    # average unit price with VAT
    @property
    def average_price(self):
        if self.on_stock != 0:
            return round(self.total_price / self.on_stock, 2)
        return 0

    @staticmethod
    def sum_total_price():
        sum_price = Article.objects.aggregate(total_price=Sum('total_price'))['total_price']
        return 0 if sum_price is None else round(sum_price, 2)

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
        validators=[MinValueValidator(0), MaxValueValidator(1000)], verbose_name='Porcí')
    procedure = models.TextField(max_length=1000, blank=True, null=True, verbose_name='Postup receptu')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe

    # used due to django-tables2 linkify
    def get_absolute_url(self):
        return reverse_lazy('kitchen:showRecipeArticles', args=[str(self.id)])

    @property
    def total_recipe_articles_price(self):
        recipes = RecipeArticle.objects.filter(recipe=self.id)
        total = 0
        for recipe in recipes:
            total += recipe.total_average_price
        return total


class RecipeArticle(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Suroviny v receptu')
        verbose_name = _('Surovina v receptu')
        ordering = ['-recipe']

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží',
                                help_text='Použité zboží')
    amount = models.DecimalField(
        decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.1'))],
        verbose_name='Množství', help_text='Množství suroviny')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe.recipe + '-  ' + self.article.article + '-  ' + str(self.amount)

    @property
    def total_average_price(self):
        return round(convertUnits(self.amount, self.unit, self.article.unit) * self.article.average_price, 2)


class DailyMenu(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Denní menu')
        verbose_name = _('Denní menu')
        ordering = ['-date', 'meal_group']

    date = models.DateField(verbose_name='Datum', help_text='Datum denního menu ve formátu dd.mm.rrrr')
    meal_group = models.ForeignKey(MealGroup, on_delete=models.CASCADE, verbose_name='Skupina strávníka',
                                   help_text='Skupina pro kterou se připravuje jídlo')
    meal_type = models.ForeignKey(MealType, on_delete=models.CASCADE, verbose_name='Druh jídla',
                                  help_text='Druh jídla v rámci dne')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.date) + ' - ' + self.meal_type.meal_type + ' - ' + self.meal_group.meal_group


class DailyMenuRecipe(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Recepty denního menu')
        verbose_name = _('Recepty denního menu')
        ordering = ['-recipe']

    daily_menu = models.ForeignKey(DailyMenu, on_delete=models.CASCADE, verbose_name='Denní menu')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name='Recept',
                               help_text='Vybraný recept')
    amount = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(1000)],
                                              verbose_name='Porcí', help_text='Počet porcí')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return self.recipe.recipe + ' - ' + str(self.amount)


class StockIssue(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Výdejky')
        verbose_name = _('Výdejka')
        ordering = ['-created']

    user_created = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='usicreated', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Vyskladněno')
    date_approved = models.DateField(blank=True, null=True, verbose_name='Datum vyskladnění')
    user_approved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='usiapproved', verbose_name='Vyskladnil')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        stock_issue_articles = StockIssueArticle.objects.filter(stock_issue=self.id)
        return round(totalRecipeArticlePrice(stock_issue_articles, 1), 2)

    def consolidateByArticle(self):
        # select all articles where count > 1
        # group by article_id and sum amount and average_unit_price
        articles_to_consolidate = StockIssueArticle.objects.filter(
            stock_issue_id=self.pk).values('article_id').annotate(average_unit_price=Min('average_unit_price'), total=Count('article_id'), sumAmount=Sum('amount')).filter(total__gt=1)
        article_ids = []
        for article in articles_to_consolidate:
            article_ids.append(article['article_id'])
        # remove all articles where count > 1
        StockIssueArticle.objects.filter(stock_issue_id=self.pk, article_id__in=article_ids).delete()
        # insert consolidated articles
        for article in articles_to_consolidate:
            x = StockIssueArticle(
                stock_issue=self,
                article=Article.objects.filter(pk=article['article_id']).get(),
                amount=article['sumAmount'],
                unit=Article.objects.filter(pk=article['article_id']).get().unit,
                average_unit_price=article['average_unit_price'],
                comment='consolidated article'
            )
            x.save()
        return len(StockIssueArticle.objects.filter(stock_issue_id=self.pk))

    @staticmethod
    def createFromDailyMenu(daily_menus, date, user):
        with transaction.atomic():
            # save the StockIssue
            stock_issue = StockIssue(comment="Pro " + date, user_created=user)
            stock_issue.save()
            # save all StockIssue Articles
            daily_menu_recipes = DailyMenuRecipe.objects.select_related('recipe').filter(daily_menu__in=daily_menus)
            for daily_menu_recipe in daily_menu_recipes:
                recipe_articles = RecipeArticle.objects.filter(recipe_id=daily_menu_recipe.recipe_id)
                for recipe_article in recipe_articles:
                    # get the coeficient between daily menu amount and recipe amount
                    recipe_article_coeficient = Decimal(daily_menu_recipe.amount / recipe_article.recipe.norm_amount)
                    recipe_article_amount = convertUnits(recipe_article.amount, recipe_article.unit,
                                                         recipe_article.article.unit) * recipe_article_coeficient
                    stock_issue_article = StockIssueArticle(
                        stock_issue=stock_issue,
                        article=recipe_article.article,
                        amount=recipe_article_amount,
                        unit=recipe_article.article.unit,
                        average_unit_price=recipe_article.article.average_price,
                        comment=""
                    )
                    stock_issue_article.save()
            count = stock_issue.consolidateByArticle()
        return count

    @staticmethod
    def updateStockIssueArticleAverageUnitPrice(stock_issue_id):
        stock_issue_articles = StockIssueArticle.objects.filter(stock_issue_id=stock_issue_id)
        print("def updateStockIssueArticleAverageUnitPrice(stock_issue_id):",
              stock_issue_id, len(stock_issue_articles), stock_issue_articles)
        for stock_issue_article in stock_issue_articles:
            print(stock_issue_article, "aktualizace z", stock_issue_article.average_unit_price,
                  "na", stock_issue_article.article.average_price)
            stock_issue_article.average_unit_price = stock_issue_article.article.average_price
            stock_issue_article.save()

    @staticmethod
    def updateArticleOnStock(stock_id, fake):
        stock_articles = StockIssueArticle.objects.filter(stock_issue=stock_id)
        messages = ''
        for stock_article in stock_articles:
            article = Article.objects.filter(pk=stock_article.article.id).get()
            converted_amount = convertUnits(stock_article.amount, stock_article.unit, article.unit)
            if article.on_stock < 0 or article.on_stock - converted_amount < 0:
                messages += "{} - na výdejce {}, na skladu {}<br/>".format(
                    stock_article.article, converted_amount, article.on_stock)
            if not fake:
                new_total_price = convertUnits(stock_article.total_average_price_with_vat, stock_article.unit,
                                               article.unit)
                article.on_stock -= round(converted_amount,2)
                article.total_price -= round(new_total_price,2)
                article.save()
                update_change_reason(article, 'Výdejka')
        return messages


class StockReceipt(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Příjemky')
        verbose_name = _('Příjemka')
        ordering = ['-created']

    date_created = models.DateField(default=datetime.date.today, verbose_name='Datum založení')
    user_created = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='usrcreated', verbose_name='Vytvořil')
    approved = models.BooleanField(default=False, blank=True, null=True, verbose_name='Naskladněno')
    date_approved = models.DateField(blank=True, null=True, verbose_name='Datum naskladnění')
    user_approved = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='usrapproved', verbose_name='Naskladnil')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    def __str__(self):
        return str(self.created)

    @property
    def total_price(self):
        stock_receipt_articles = StockReceiptArticle.objects.filter(stock_receipt=self.id)
        total_price = 0
        for stock_receipt_article in stock_receipt_articles:
            total_price += stock_receipt_article.total_price_with_vat
        return round(total_price, 2)

    @staticmethod
    def updateArticleOnStock(stock_id):
        stock_articles = StockReceiptArticle.objects.filter(stock_receipt=stock_id)
        for stock_article in stock_articles:
            article = Article.objects.filter(pk=stock_article.article.id).get()
            converted_amount = convertUnits(stock_article.amount, stock_article.unit, article.unit)
            new_total_price = convertUnits(stock_article.total_price_with_vat, stock_article.unit, article.unit)
            # print("StockReceipt - mnozství: ", article.on_stock, "+", converted_amount,
            #       " - cena: ", article.total_price, "+", new_total_price)
            article.on_stock += round(converted_amount,2)
            article.total_price += round(new_total_price,2)
            article.save()
            update_change_reason(article, 'Příjemka')


class StockIssueArticle(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Zboží na výdejce')
        verbose_name = _('Zboží na výdejce')
        ordering = ['-article__article']

    stock_issue = models.ForeignKey(StockIssue, on_delete=models.CASCADE, verbose_name='Výdejka')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží')
    amount = models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Množství')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    average_unit_price = models.DecimalField(max_digits=10, decimal_places=2,
                                             blank=True, null=True, verbose_name='Průměrná jednotková cena s DPH')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    @property
    def total_average_price_with_vat(self):
        if self.amount is not None and self.average_unit_price is not None:
            return round(self.amount * self.average_unit_price, 2)
        return 0

    # def clean(self):
    #     article = Article.objects.filter(pk=self.article.id).values_list('on_stock', 'unit')
    #     on_stock = article[0][0]
    #     stock_unit = article[0][1]
    #     issued_amount = convertUnits(self.amount, self.unit, stock_unit)
    #     if on_stock - issued_amount < 0:
    #         raise ValidationError(
    #             {'amount': _("Na skladu je {0} {1} a vydáváte {2} {1}.".format(on_stock, stock_unit, issued_amount))})

    def __str__(self):
        return self.article.article + ' - ' + str(self.amount) + self.unit


class StockReceiptArticle(TimeStampedModel):

    class Meta:
        verbose_name_plural = _('Zboží na příjemce')
        verbose_name = _('Zboží na příjemce')
        ordering = ['-id']

    stock_receipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, verbose_name='Příjemka')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name='Zboží')
    amount = models.DecimalField(decimal_places=2, max_digits=8, validators=[
        MinValueValidator(Decimal('0.1'))], verbose_name='Množství')
    unit = models.CharField(max_length=2, choices=UNIT, verbose_name='Jednotka')
    price_without_vat = models.DecimalField(max_digits=10, decimal_places=2, validators=[
        MinValueValidator(Decimal('0.1'))], verbose_name='Jednotková cena bez DPH')
    vat = models.ForeignKey(VAT, default=2, on_delete=models.CASCADE, verbose_name='DPH')
    comment = models.CharField(max_length=200, blank=True, null=True, verbose_name='Poznámka')

    @property
    def price_with_vat(self):
        if self.price_without_vat is not None and self.vat.percentage is not None:
            return self.price_without_vat + self.price_without_vat * self.vat.percentage/100
        return 0

    @property
    def total_price_with_vat(self):
        if self.price_with_vat is not None and self.amount is not None:
            return round(self.price_with_vat * self.amount, 2)
        return 0

    def __str__(self):
        return self.article.article + ' - ' + str(self.amount) + self.unit
