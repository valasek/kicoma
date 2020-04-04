import django_tables2 as tables
from .models import RecipeBook
import django_filters


class RecipeBookTable(tables.Table):
    change = tables.TemplateColumn('''
    <a href="/recipe/update/{{ record.id }}">Upravit</a> / 
    <a href="/recipe/delete/{{ record.id }}" onclick="return confirm('Skutečně chcete tuto položku odstranit?')">Odstranit</a>''',
                                   verbose_name=u'Akce', )

    class Meta:
        model = RecipeBook
        template_name = "django_tables2/bootstrap4.html"
        fields = ("code", "name", "norm_amount", "change")


class RecipeBookFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='contains')
    code = django_filters.CharFilter(lookup_expr='contains')

    class Meta:
        model = RecipeBook
        fields = fields = ("code", "name")
