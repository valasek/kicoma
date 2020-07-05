import django_tables2 as tables
import django_filters
from .models import Recipe, Ingredient, StockReceipt, StockIssue, Article, DailyMenu, Item, DailyMenuRecipe


class ArticleTable(tables.Table):
    # vat__percentage = tables.Column(verbose_name='DPH')
    averagePrice = tables.Column(verbose_name='Průměrná jednotková cena')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergény')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "onStock", "minOnStock", "unit", "averagePrice",
                  "totalPrice", "allergens", "comment", "change")

    def render_averagePrice(self, value, record):
        return '{} Kč / {}'.format(value, record.unit)


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
        fields = ("recipe", "norm_amount", "comment", "change")


class RecipeFilter(django_filters.FilterSet):
    recipe = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ("recipe",)


class RecipeIngredientTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/updateingredient/{{ record.id }}">Upravit</a>
            | <a href="/kitchen/recipe/deleteingredient/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Ingredient
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "unit", "change")


class RecipeIngredientFilter(django_filters.FilterSet):
    article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Ingredient
        fields = ("article",)


class DailyMenuTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/update/{{ record.id }}">Upravit</a>
        <a href="/kitchen/dailymenu/recipelist/{{ record.id }}">Zobrazit recepty</a>
        <a href="/kitchen/dailymenu/delete/{{ record.id }}">Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenu
        template_name = "django_tables2/bootstrap4.html"
        fields = ("date", "mealGroup", "mealType", "comment", "change")


class DailyMenuFilter(django_filters.FilterSet):
    date = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = DailyMenu
        fields = ("date", )


class DailyMenuRecipeTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/updaterecipe/{{ record.id }}">Upravit</a>
        <a href="/kitchen/dailymenu/deleterecipe/{{ record.id }}" >Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenuRecipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("recipe", "amount", "change")


class DailyMenuRecipeFilter(django_filters.FilterSet):
    recipe = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = DailyMenuRecipe
        fields = ("recipe", )


class StockIssueTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/update/{{ record.id }}">Upravit poznámku</a>
        | <a href="/kitchen/stockissue/itemlist/{{ record.id }}">Zobrazit zboží</a>
        | <a href="/kitchen/stockissue/approve/{{ record.id }}">Schválit</a>
        | <a href="/kitchen/stockissue/print/{{ record.id }}">Tisk</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockIssue
        template_name = "django_tables2/bootstrap4.html"
        fields = ("created", "userCreated", "approved", "dateApproved", "userApproved", "comment", "change")


class StockIssueFilter(django_filters.FilterSet):
    created = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockIssue
        fields = ("created", )


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
        fields = ("created", "userCreated", "comment", "change")


class StockReceiptFilter(django_filters.FilterSet):
    created = django_filters.CharFilter(lookup_expr='icontains')
    # userCreated = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockReceipt
        fields = ("created", "userCreated", )


class StockReceiptItemTable(tables.Table):
    price_with_vat = tables.Column(verbose_name='Cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/updateitem/{{ record.id }}">Upravit</a>
            | <a href="/kitchen/stockreceipt/deleteitem/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Item
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "unit", "priceWithoutVat", "vat", "price_with_vat", "change")


class StockReceiptItemFilter(django_filters.FilterSet):
    article__article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Item
        fields = ("article__article", )
