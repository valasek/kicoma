import django_tables2 as tables
import django_filters
from .models import Recipe, StockReceipt, Article, DailyMenu


class StockReceiptTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        fields = ("dateCreated", "userCreated__name", "comment", "change")


class StockReceiptFilter(django_filters.FilterSet):
    dateCreated = django_filters.CharFilter(lookup_expr='contains')
    userCreated__name = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = StockReceipt
        fields = ("dateCreated", "userCreated__name", )


class DailyMenuTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/edit/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenu
        template_name = "django_tables2/bootstrap4.html"
        fields = ("date", "amount", "mealGroup", "mealType", "recipe", "change")


class DailyMenuFilter(django_filters.FilterSet):
    date = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = DailyMenu
        fields = ("date", )

class ArticleTable(tables.Table):
    # priceWithVat = tables.Column(verbose_name='Cena s DPH')
    # vat__percentage = tables.Column(verbose_name='DPH')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergény')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/edit/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )


    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "onStock", "averagePrice", "unit", "comment", "allergens", "change")

class ArticleFilter(django_filters.FilterSet):
    article = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a> /
        <a href="/kitchen/recipe/delete/{{ record.id }} \
            onclick="return confirm('Skutečně chcete tuto položku odstranit?')">Odstranit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("recipe", "norm_amount", "change")


class RecipeFilter(django_filters.FilterSet):
    recipe = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = Recipe
        fields = ("recipe",)
