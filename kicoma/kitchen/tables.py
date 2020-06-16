import django_tables2 as tables
import django_filters
from .models import Recipe, StockReceipt, Article


class StockReceiptTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        fields = ("createdAt", "userCreated", "comment", "change")


class StockReceiptFilter(django_filters.FilterSet):
    createdAt = django_filters.CharFilter(lookup_expr='contains')
    userCreated__name = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = StockReceipt
        fields = ("createdAt", "userCreated__name", )


class ArticleTable(tables.Table):
    # priceWithVat = tables.Column(verbose_name='Cena s DPH')
    # vat__percentage = tables.Column(verbose_name='DPH')

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        fields = ("code", "name", "onStock", "averagePrice", "unit", "comment", "allergen")

class ArticleFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = Article
        fields = ("name",)


class RecipeTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a> /
        <a href="/kitchen/recipe/delete/{{ record.id }} \
            onclick="return confirm('Skutečně chcete tuto položku odstranit?')">Odstranit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("name", "norm_amount", "change")


class RecipeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = Recipe
        fields = ("name",)
