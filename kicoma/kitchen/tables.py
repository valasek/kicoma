import django_tables2 as tables
from django_filters import FilterSet, CharFilter, DateFilter
from django.contrib.humanize.templatetags.humanize import intcomma

from .models import Recipe, RecipeArticle, StockReceipt, StockIssue, Article, DailyMenu, \
    Menu, MenuRecipe, StockIssueArticle, StockReceiptArticle, DailyMenuRecipe


class ArticleTable(tables.Table):
    average_price = tables.Column(verbose_name='Průměrná jednotková cena s DPH')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergeny')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/article/history/{{ record.id }}">Historie</a>
        | <a href="/kitchen/article/delete/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "on_stock", "min_on_stock", "average_price",
                  "total_price", "allergens", "comment", "change")

    @staticmethod
    def render_average_price(value, record):
        return '{} Kč / {}'.format(intcomma(value), record.unit)

    @staticmethod
    def render_total_price(value):
        return '{} Kč'.format(intcomma(value))

    @staticmethod
    def render_on_stock(value, record):
        return '{} {}'.format(value, record.unit)

    @staticmethod
    def render_min_on_stock(value, record):
        return '{} {}'.format(value, record.unit)


class ArticleRestrictedTable(tables.Table):
    allergen = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergeny')
    average_price = tables.Column(verbose_name='Průměrná jednotková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/restrictedupdate/{{ record.id }}">Upravit</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "unit", "min_on_stock", "allergen", "average_price", "comment", "change")

    @staticmethod
    def render_min_on_stock(value, record):
        return '{} {}'.format(value, record.unit)

    @staticmethod
    def render_average_price(value, record):
        return '{} Kč / {}'.format(intcomma(value), record.unit)


class ArticleFilter(FilterSet):
    article = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    total_recipe_articles_price = tables.Column(verbose_name='Cena receptu s DPH')
    allergens = tables.Column(verbose_name='Alergeny', empty_values=())
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/recipe/articlelist/{{ record.id }}">Zobrazit ingredience</a>
        | <a href="/kitchen/recipe/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/recipe/print/{{ record.id }}">PDF</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "norm_amount", "total_recipe_articles_price", "allergens", "change")

    @staticmethod
    def render_total_recipe_articles_price(value):
        return '{} Kč'.format(intcomma(value))

    @staticmethod
    def render_allergens(record):
        return record.get_allergens(record.id)


class RecipeFilter(FilterSet):
    recipe = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ("recipe",)


class RecipeArticleTable(tables.Table):
    # average_price = tables.Column(accessor="article.average_price", verbose_name="Průměrná jednotková cena s DPH")
    total_average_price = tables.Column(verbose_name="Celková cena s DPH")
    change = tables.TemplateColumn(
        '''<a href="/kitchen/recipe/updatearticle/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/recipe/deletearticle/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = RecipeArticle
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "total_average_price", "comment", "change")

    @staticmethod
    def render_amount(value, record):
        return '{} {}'.format(value, record.unit)

    @staticmethod
    def render_average_price(value, record):
        return '{} Kč / {}'.format(intcomma(value), record.article.unit)

    @staticmethod
    def render_total_average_price(value):
        return '{} Kč'.format(intcomma(value))


class DailyMenuTable(tables.Table):
    max_amount_number = tables.Column(verbose_name='Počet porcí', empty_values=())
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/dailymenu/recipelist/{{ record.id }}">Zobrazit recepty</a>
        | <a href="/kitchen/report/print/foodconsumption?date={{ record.date }}&meal_group=">PDF - spotřeba potravin</a>
        | <a href="/kitchen/dailymenu/delete/{{ record.id }}">Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenu
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("date", "meal_group", "meal_type", "max_amount_number", "change")

    @staticmethod
    def render_max_amount_number(record):
        # daily_menus = DailyMenu.objects.filter(daily_menu=record.id).select_related('meal_group', 'meal_type')
        # return daily_menus.max_amount_number(record.id)
        return DailyMenu.max_amount_number(record.id)


class DailyMenuFilter(FilterSet):
    date = DateFilter(lookup_expr='contains')

    class Meta:
        model = DailyMenu
        fields = ("date", )


class DailyMenuRecipeTable(tables.Table):
    recipe = tables.Column(linkify=True)
    change = tables.TemplateColumn(
        '''<a href="/kitchen/dailymenu/updaterecipe/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/dailymenu/deleterecipe/{{ record.id }}" >Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = DailyMenuRecipe
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "amount", "change")


class MenuTable(tables.Table):
    rc = tables.Column(verbose_name='Počet receptů', empty_values=())
    change = tables.TemplateColumn(
        '''<a href="/kitchen/menu/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/menu/recipelist/{{ record.id }}">Zobrazit recepty</a>
        | <a href="/kitchen/menu/delete/{{ record.id }}">Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = Menu
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("menu", "meal_type", "rc", "comment", "change")

    @staticmethod
    def render_rc(record):
        return record.recipe_count


class MenuRecipeTable(tables.Table):
    recipe = tables.Column(linkify=True)
    change = tables.TemplateColumn(
        '''<a href="/kitchen/menu/updaterecipe/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/menu/deleterecipe/{{ record.id }}" >Vymazat</a>
        ''',
        verbose_name=u'Akce', )

    class Meta:
        model = MenuRecipe
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "amount", "change")


class StockIssueTable(tables.Table):
    total_price = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/update/{{ record.id }}">Poznámka</a>
        | <a href="/kitchen/stockissue/articlelist/{{ record.id }}">Zobrazit zboží</a>
        {% load auth_extras %}
        {% if request.user|has_group:"stockkeeper" %}
        | <a href="/kitchen/stockissue/refresh/{{ record.id }}">Aktualizovat</a>
        | <a href="/kitchen/stockissue/approve/{{ record.id }}">Vyskladnit</a>
        {% endif %}
        | <a href="/kitchen/stockissue/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/stockissue/print/{{ record.id }}">PDF</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockIssue
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("created", "user_created", "approved", "date_approved",
                  "user_approved", "total_price", "comment", "change")

    @staticmethod
    def render_total_price(value):
        return '{} Kč'.format(intcomma(intcomma(value)))

    @staticmethod
    def render_created(value):
        return value.strftime('%d.%m.%Y')


class StockIssueFilter(FilterSet):
    created = DateFilter(lookup_expr='contains')

    class Meta:
        model = StockIssue
        fields = ("approved", "created", "user_approved")


class StockIssueArticleTable(tables.Table):
    total_average_price_with_vat = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/updatearticle/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/stockissue/deletearticle/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockIssueArticle
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "average_unit_price", "total_average_price_with_vat", "change")

    @staticmethod
    def render_amount(value, record):
        return '{} {}'.format(value, record.unit)

    @staticmethod
    def render_average_unit_price(value, record):
        return '{} Kč / {}'.format(intcomma(value), record.article.unit)

    @staticmethod
    def render_total_average_price_with_vat(value):
        return '{} Kč'.format(intcomma(value))


class StockReceiptTable(tables.Table):
    total_price = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/stockreceipt/articlelist/{{ record.id }}">Zobrazit zboží</a>
        | <a href="/kitchen/stockreceipt/approve/{{ record.id }}">Naskladnit</a>
        | <a href="/kitchen/stockreceipt/delete/{{ record.id }}">Vymazat</a>
        | <a href="/kitchen/stockreceipt/print/{{ record.id }}">PDF</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("date_created", "user_created", "approved", "date_approved",
                  "user_approved", "total_price", "comment", "change")

    @staticmethod
    def render_total_price(value):
        return '{} Kč'.format(intcomma(value))


class StockReceiptFilter(FilterSet):
    date_created = DateFilter(lookup_expr='contains')
    # user_created = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockReceipt
        fields = ("date_created", "user_created", )


class StockReceiptArticleTable(tables.Table):
    price_with_vat = tables.Column(verbose_name='Jednotková cena s DPH')
    total_price_with_vat = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockreceipt/updatearticle/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/stockreceipt/deletearticle/{{ record.id }}">Vymazat</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = StockReceiptArticle
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "price_without_vat", "vat",
                  "price_with_vat", "total_price_with_vat", "change")

    @staticmethod
    def render_amount(value, record):
        return '{} {}'.format(value, record.unit)

    @staticmethod
    def render_price_without_vat(value):
        return '{} Kč'.format(intcomma(value))

    @staticmethod
    def render_price_with_vat(value):
        return '{} Kč'.format(intcomma(value))

    @staticmethod
    def render_total_price_with_vat(value):
        return '{} Kč'.format(intcomma(value))
