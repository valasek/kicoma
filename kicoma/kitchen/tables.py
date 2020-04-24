import django_tables2 as tables
from .models import Recipe
import django_filters


class RecipeTable(tables.Table):
    change = tables.TemplateColumn('''
    <a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a> /
    <a href="/kitchen/recipe/delete/{{ record.id }}">Odstranit</a>''',
                                   verbose_name=u'Akce', )
    # <a href="/kitchen/recipe/delete/{{ record.id }}" onclick="return confirm('Skutečně chcete tuto položku odstranit?')">Odstranit</a>''',

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
