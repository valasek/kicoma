import django_tables2 as tables
from django_filters import FilterSet, CharFilter, DateFilter
from django.contrib.humanize.templatetags.humanize import intcomma

from .models import Recipe, RecipeArticle, StockReceipt, StockIssue, Article, DailyMenu, \
    StockIssueArticle, StockReceiptArticle, DailyMenuRecipe


class ArticleTable(tables.Table):
    average_price = tables.Column(verbose_name='Průměrná jednotková cena s DPH')
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name='Alergény')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/article/update/{{ record.id }}">Upravit</a>
        | <a href="/kitchen/article/history/{{ record.id }}">Historie</a>''',
        verbose_name=u'Akce', )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap4.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "on_stock", "min_on_stock", "average_price",
                  "total_price", "allergens", "comment", "change")

    def render_average_price(self, value, record):
        return '{} Kč / {}'.format(intcomma(value), record.unit)

    def render_total_price(self, value, record):
        return '{} Kč'.format(intcomma(value))

    def render_on_stock(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_min_on_stock(self, value, record):
        return '{} {}'.format(value, record.unit)


class ArticleFilter(FilterSet):
    article = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    total_recipe_articles_price = tables.Column(verbose_name='Cena receptu s DPH')
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
        fields = ("recipe", "norm_amount", "total_recipe_articles_price", "comment", "change")

    def render_total_recipe_articles_price(self, value, record):
        return '{} Kč'.format(intcomma(value))


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

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_average_price(self, value, record):
        return '{} Kč / {}'.format(intcomma(value), record.article.unit)

    def render_total_average_price(self, value, record):
        return '{} Kč'.format(intcomma(value))


class DailyMenuTable(tables.Table):
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
        fields = ("date", "meal_group", "meal_type", "comment", "change")


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


class StockIssueTable(tables.Table):
    total_price = tables.Column(verbose_name='Celková cena s DPH')
    change = tables.TemplateColumn(
        '''<a href="/kitchen/stockissue/update/{{ record.id }}">Upravit poznámku</a>
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

    def render_total_price(self, value, record):
        return '{} Kč'.format(intcomma(intcomma(value)))


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

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_average_unit_price(self, value, record):
        return '{} Kč / {}'.format(intcomma(value), record.article.unit)

    def render_total_average_price_with_vat(self, value, record):
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

    def render_total_price(self, value, record):
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

    def render_amount(self, value, record):
        return '{} {}'.format(value, record.unit)

    def render_price_without_vat(self, value, record):
        return '{} Kč'.format(intcomma(value))

    def render_price_with_vat(self, value, record):
        return '{} Kč'.format(intcomma(value))

    def render_total_price_with_vat(self, value, record):
        return '{} Kč'.format(intcomma(value))
