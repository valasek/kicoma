import django_tables2 as tables
import django_filters
from .models import Recipe, Ingredient, StockReceipt, StockIssue, Article, DailyMenu, Item


class StockIssueTable(tables.Table):
    change = tables.TemplateColumn(
        '''Akce''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockIssue
        template_name = "django_tables2/bootstrap4.html"
        fields = ["__all__"]


class StockReceiptTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/update/{{ record.id }}">Upravit poznámku</a>
        | <a href="/kitchen/stockreceipt/itemlist/{{ record.id }}">Zobrazit položky</a>
        | <a href="/kitchen/stockreceipt/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/stockreceipt/print/{{ record.id }}">Tisk</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        fields = ("userCreated__name", "comment", "modified", "change")


class StockReceiptItemTable(tables.Table):
    price_with_vat = tables.Column(verbose_name='Cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/updateitem/{{ record.id }}">Upravit</a>
            | <a href="/kitchen/stockreceipt/deleteitem/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Item
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "unit", "priceWithoutVat", "vat", "price_with_vat", "comment", "change")


class StockReceiptFilter(django_filters.FilterSet):
    created = django_filters.CharFilter(lookup_expr='icontains')
    userCreated__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockReceipt
        fields = ("created", "userCreated__name", )


class StockReceiptItemFilter(django_filters.FilterSet):
    article__article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Item
        fields = ("article__article", )


class DailyMenuTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenu
        template_name = "django_tables2/bootstrap4.html"
        fields = ("date", "amount", "mealGroup", "mealType", "recipe", "modified", "change")


class DailyMenuFilter(django_filters.FilterSet):
    date = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = DailyMenu
        fields = ("date", )


class ArticleTable(tables.Table):
    # vat__percentage = tables.Column(verbose_name='DPH')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergény')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "onStock", "averagePrice", "unit", "comment", "allergens", "modified", "change")


class ArticleFilter(django_filters.FilterSet):
    article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/recipe/ingredientlist/{{ record.id }}">Zobrazit ingredience</a>
        | <a href="/kitchen/recipe/delete/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )


    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("recipe", "norm_amount", "modified", "change")


class RecipeIngredientTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/updateingredient/{{ record.id }}">Upravit</a>
            | <a href="/kitchen/recipe/deleteingredient/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Ingredient
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "unit", "change")

class RecipeFilter(django_filters.FilterSet):
    recipe = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ("recipe",)


class RecipeIngredientFilter(django_filters.FilterSet):
    article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ingredient
        fields = ("article",)
