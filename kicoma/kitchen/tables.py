import django_tables2 as tables
import django_filters

from .models import Recipe, Ingredient, StockReceipt, StockIssue, Article, DailyMenu, Item, DailyMenuRecipe


class ArticleTable(tables.Table):
    # vat__percentage = tables.Column(verbose_name='DPH')
    averagePrice = tables.Column(verbose_name='Průměrná jednotková cena s DPH')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergény')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/update/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "onStock", "minOnStock", "averagePrice",
                  "totalPrice", "allergens", "comment", "change")

    def render_averagePrice(self, value, record):
        return '{} Kč / {}'.format(value, record.unit)

    def render_totalPrice(self, value, record):
        return '{} Kč'.format(value)

    def render_onStock(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_minOnStock(self, value, record):
        return '{} {}'.format(value, record.unit)


class ArticleFilter(django_filters.FilterSet):
    article = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    recipePrice = tables.Column(verbose_name='Cena receptu s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/recipe/ingredientlist/{{ record.id }}">Zobrazit ingredience</a>
        | <a href="/kitchen/recipe/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/recipe/print/{{ record.id }}">Tisk</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("recipe", "norm_amount", "recipePrice", "comment", "change")

    def render_recipePrice(self, value, record):
        return '{} Kč'.format(value)


class RecipeFilter(django_filters.FilterSet):
    recipe = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ("recipe",)


class RecipeIngredientTable(tables.Table):
    average_price = tables.Column(accessor="article.averagePrice", verbose_name="Průměrná jednotková cena s DPH")
    total_average_price = tables.Column(verbose_name="Celková cena s DPH")
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/updateingredient/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/recipe/deleteingredient/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Ingredient
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "average_price", "total_average_price", "change")

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_average_price(self, value, record):
        return '{} Kč / {}'.format(value, record.article.unit)

    def render_total_average_price(self, value, record):
        return '{} Kč'.format(value)


class DailyMenuTable(tables.Table):
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/dailymenu/recipelist/{{ record.id }}">Zobrazit recepty</a>
        | <a href="/kitchen/dailymenu/delete/{{ record.id }}">Vymazat</a>
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
        | <a href="/kitchen/dailymenu/deleterecipe/{{ record.id }}" >Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenuRecipe
        template_name = "django_tables2/bootstrap4.html"
        fields = ("recipe", "amount", "change")


class StockIssueTable(tables.Table):
    total_price = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/update/{{ record.id }}">Upravit poznámku</a>
        | <a href="/kitchen/stockissue/itemlist/{{ record.id }}">Zobrazit zboží</a>
        | <a href="/kitchen/stockissue/approve/{{ record.id }}">Vyskladnit</a>
        | <a href="/kitchen/stockissue/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/stockissue/print/{{ record.id }}">Tisk</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockIssue
        template_name = "django_tables2/bootstrap4.html"
        fields = ("created", "userCreated", "approved", "dateApproved",
                  "userApproved", "total_price", "comment", "change")

    def render_total_price(self, value, record):
        return '{} Kč'.format(value)

class StockIssueFilter(django_filters.FilterSet):
    created = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockIssue
        fields = ("approved", "created", "userApproved")


class StockIssueItemTable(tables.Table):
    average_price = tables.Column(accessor="article.averagePrice", verbose_name="Průměrná jednotková cena s DPH")
    total_average_price_with_vat = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/updateitem/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/stockissue/deleteitem/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Item
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "average_price", "total_average_price_with_vat", "change")

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_average_price(self, value, record):
        return '{} Kč / {}'.format(value, record.article.unit)

    def render_total_average_price_with_vat(self, value, record):
        return '{} Kč'.format(value)


class StockReceiptTable(tables.Table):
    total_price = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/update/{{ record.id }}">Upravit poznámku</a>
        | <a href="/kitchen/stockreceipt/itemlist/{{ record.id }}">Zobrazit zboží</a>
        | <a href="/kitchen/stockreceipt/approve/{{ record.id }}">Naskladnit</a>
        | <a href="/kitchen/stockreceipt/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/stockreceipt/print/{{ record.id }}">Tisk</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        fields = ("created", "userCreated", "approved", "dateApproved",
                  "userApproved", "total_price", "comment", "change")

    def render_total_price(self, value, record):
        return '{} Kč'.format(value)


class StockReceiptFilter(django_filters.FilterSet):
    created = django_filters.CharFilter(lookup_expr='icontains')
    # userCreated = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockReceipt
        fields = ("created", "userCreated", )


class StockReceiptItemTable(tables.Table):
    price_with_vat = tables.Column(verbose_name='Jednotková cena s DPH')
    total_price_with_vat = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/updateitem/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/stockreceipt/deleteitem/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Item
        template_name = "django_tables2/bootstrap4.html"
        fields = ("article", "amount", "priceWithoutVat", "vat",
                  "price_with_vat", "total_price_with_vat", "change")

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_priceWithoutVat(self, value, record):
        return '{} Kč'.format(value)

    def render_price_with_vat(self, value, record):
        return '{} Kč'.format(value)

    def render_total_price_with_vat(self, value, record):
        return '{} Kč'.format(value)
