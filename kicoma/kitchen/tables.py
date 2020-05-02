import django_tables2 as tables
import django_filters
from .models import Recipe, StockReceipt


class StockReceiptTable(tables.Table):

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        fields = ("createdAt", "userCreated", "comment")


class StockReceiptFilter(django_filters.FilterSet):
    createdAt = django_filters.CharFilter(lookup_expr='contains')
    userCreated__name = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = StockReceipt
        fields = ("createdAt", "userCreated__name", )


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
    code = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = Recipe
        fields = ("name",)
