import django_tables2 as tables
from django import forms
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_filters import CharFilter, DateFilter, FilterSet

from .models import (
    Article,
    DailyMenu,
    DailyMenuRecipe,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
)

LABEL_EDIT = _("Upravit")
LABEL_HISTORY = _("Historie")
LABEL_DELETE = _("Vymazat")
LABEL_SHOW_INGREDIENTS = _("Zobrazit ingredience")
LABEL_SHOW_RECIPES = _("Zobrazit recepty")
LABEL_NOTE = _("Poznámka")
LABEL_SHOW_ARTICLES = _("Zobrazit zboží")
LABEL_REFRESH = _("Aktualizovat")
LABEL_ISSUE = _("Vyskladnit")
LABEL_RECEIPT = _("Naskladnit")

class ArticleTable(tables.Table):
    average_price = tables.Column(verbose_name=_('Průměrná jednotková cena s DPH'))
    allergens = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name=_('Alergeny'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/article/update/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/article/history/{record.id}">{LABEL_HISTORY}</a> | '
            f'<a href="/kitchen/article/delete/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "on_stock", "min_on_stock", "average_price",
                  "total_price", "allergens", "comment", "change")

    @staticmethod
    def render_average_price(value, record):
        return f'{intcomma(value)} Kč / {record.unit}'

    @staticmethod
    def render_total_price(value):
        return f'{intcomma(value)} Kč'

    @staticmethod
    def render_on_stock(value, record):
        return f'{value} {record.unit}'

    @staticmethod
    def render_min_on_stock(value, record):
        return f'{value} {record.unit}'


class ArticleRestrictedTable(tables.Table):
    allergen = tables.TemplateColumn('''{{record.display_allergens}}''', verbose_name=_('Alergeny'))
    average_price = tables.Column(verbose_name=_('Průměrná jednotková cena s DPH'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/article/restrictedupdate/{record.id}">{LABEL_EDIT}</a>'
        )

    class Meta:
        model = Article
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "unit", "min_on_stock", "allergen", "average_price", "comment", "change")

    @staticmethod
    def render_min_on_stock(value, record):
        return f'{value} {record.unit}'

    @staticmethod
    def render_average_price(value, record):
        return f'{intcomma(value)} Kč / {record.unit}'


class ArticleFilter(FilterSet):
    article = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Article
        fields = ("article",)


class RecipeTable(tables.Table):
    total_recipe_articles_price = tables.Column(verbose_name=_('Cena receptu s DPH'))
    allergens = tables.Column(verbose_name=_('Alergeny'), empty_values=())
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/recipe/update/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/recipe/articlelist/{record.id}">{LABEL_SHOW_INGREDIENTS}</a> | '
            f'<a href="/kitchen/recipe/delete/{record.id}">{LABEL_DELETE}</a> | '
            f'<a href="/kitchen/recipe/print/{record.id}">PDF</a>'
        )

    class Meta:
        model = Recipe
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "norm_amount", "total_recipe_articles_price", "allergens", "change")

    @staticmethod
    def render_total_recipe_articles_price(value):
        return f'{intcomma(value)} Kč'

    @staticmethod
    def render_allergens(record):
        return record.allergens()


class RecipeFilter(FilterSet):
    recipe = CharFilter(lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = ("recipe",)


class RecipeArticleTable(tables.Table):
    # average_price = tables.Column(accessor="article.average_price", verbose_name="Průměrná jednotková cena s DPH")
    total_average_price = tables.Column(verbose_name=_("Celková cena s DPH"))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/recipe/updatearticle/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/recipe/deletearticle/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = RecipeArticle
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "total_average_price", "comment", "change")

    @staticmethod
    def render_amount(value, record):
        return f'{value} {record.unit}'

    @staticmethod
    def render_average_price(value, record):
        return f'{intcomma(value)} Kč / {record.article.unit}'

    @staticmethod
    def render_total_average_price(value):
        return f'{intcomma(value)} Kč'


class DailyMenuTable(tables.Table):
    max_amount_number = tables.Column(verbose_name=_('Počet porcí'), empty_values=())
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/dailymenu/update/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/dailymenu/recipelist/{record.id}">{LABEL_SHOW_RECIPES}</a> | '
            f'<a href="/kitchen/dailymenu/delete/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = DailyMenu
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("date", "meal_group", "meal_type", "max_amount_number", "change")

    @staticmethod
    def render_max_amount_number(record):
        value = getattr(record, 'max_amount_number', None)
        return value if value is not None else '-'


class DailyMenuFilter(FilterSet):
    date = DateFilter(
        lookup_expr='contains',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-control',
                'placeholder': _('Vyber datum'),
                'type': 'date'
            }
        )
    )

    class Meta:
        model = DailyMenu
        fields = ("date", )


class DailyMenuRecipeTable(tables.Table):
    recipe = tables.Column(linkify=True)
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/dailymenu/updaterecipe/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/dailymenu/deleterecipe/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = DailyMenuRecipe
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "amount", "change")


class MenuTable(tables.Table):
    rc = tables.Column(verbose_name=_('Počet receptů'), empty_values=())
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/menu/update/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/menu/recipelist/{record.id}">{LABEL_SHOW_RECIPES}</a> | '
            f'<a href="/kitchen/menu/delete/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = Menu
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("menu", "meal_type", "rc", "comment", "change")

    @staticmethod
    def render_rc(record):
        return record.recipe_count


class MenuRecipeTable(tables.Table):
    recipe = tables.Column(linkify=True)
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/menu/updaterecipe/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/menu/deleterecipe/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = MenuRecipe
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("recipe", "amount", "change")


class StockIssueTable(tables.Table):
    total_price = tables.Column(verbose_name=_('Celková cena s DPH'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        links = [
            f'<a href="/kitchen/stockissue/update/{record.id}">{LABEL_NOTE}</a>',
            f'<a href="/kitchen/stockissue/articlelist/{record.id}">{LABEL_SHOW_ARTICLES}</a>',
        ]

        # if you still need role-based conditions, handle them here in Python
        user = getattr(self, "request", None).user if hasattr(self, "request") else None
        if user and user.groups.filter(name="stockkeeper").exists():
            links.append(f'<a href="/kitchen/stockissue/refresh/{record.id}">{LABEL_REFRESH}</a>')
            links.append(f'<a href="/kitchen/stockissue/approve/{record.id}">{LABEL_ISSUE}</a>')

        links.extend([
            f'<a href="/kitchen/stockissue/delete/{record.id}">{LABEL_DELETE}</a>',
            f'<a href="/kitchen/stockissue/print/{record.id}">PDF</a>',
        ])

        return mark_safe(" | ".join(links))

    class Meta:
        model = StockIssue
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("created", "user_created", "approved", "date_approved",
                  "user_approved", "total_price", "comment", "change")

    @staticmethod
    def render_total_price(value):
        return f'{intcomma(intcomma(value))} Kč'

    @staticmethod
    def render_created(value):
        return value.strftime('%d.%m.%Y')


class StockIssueFilter(FilterSet):
    created = DateFilter(
        lookup_expr='contains',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-control',
                'placeholder': _('Vyber datum'),
                'type': 'date'
            }
        )
    )

    class Meta:
        model = StockIssue
        fields = ("approved", "created", "user_approved")


class StockIssueArticleTable(tables.Table):
    total_average_price_with_vat = tables.Column(verbose_name=_('Celková cena s DPH'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/stockissue/updatearticle/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/stockissue/deletearticle/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = StockIssueArticle
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "average_unit_price", "total_average_price_with_vat", "change")

    @staticmethod
    def render_amount(value, record):
        return f'{value} {record.unit}'

    @staticmethod
    def render_average_unit_price(value, record):
        return f'{intcomma(value)} Kč / {record.article.unit}'

    @staticmethod
    def render_total_average_price_with_vat(value):
        return f'{intcomma(value)} Kč'


class StockReceiptTable(tables.Table):
    total_price = tables.Column(verbose_name=_('Celková cena s DPH'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/stockreceipt/update/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/stockreceipt/articlelist/{record.id}">{LABEL_SHOW_ARTICLES}</a> | '
            f'<a href="/kitchen/stockreceipt/approve/{record.id}">{LABEL_RECEIPT}</a> | '
            f'<a href="/kitchen/stockreceipt/delete/{record.id}">{LABEL_DELETE}</a> | '
            f'<a href="/kitchen/stockreceipt/print/{record.id}">PDF</a>'
        )

    class Meta:
        model = StockReceipt
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("date_created", "user_created", "approved", "date_approved",
                  "user_approved", "total_price", "comment", "change")

    @staticmethod
    def render_total_price(value):
        return f'{intcomma(value)} Kč'


class StockReceiptFilter(FilterSet):
    date_created = DateFilter(
        lookup_expr='contains',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-control',
                'placeholder': _('Vyber datum'),
                'type': 'date'
            }
        )
    )

    class Meta:
        model = StockReceipt
        fields = ("date_created", "user_created", )


class StockReceiptArticleTable(tables.Table):
    price_with_vat = tables.Column(verbose_name=_('Jednotková cena s DPH'))
    total_price_with_vat = tables.Column(verbose_name=_('Celková cena s DPH'))
    change = tables.Column(empty_values=(), verbose_name=_("Akce"))

    def render_change(self, record):
        return mark_safe(
            f'<a href="/kitchen/stockreceipt/updatearticle/{record.id}">{LABEL_EDIT}</a> | '
            f'<a href="/kitchen/stockreceipt/deletearticle/{record.id}">{LABEL_DELETE}</a>'
        )

    class Meta:
        model = StockReceiptArticle
        template_name = "django_tables2/bootstrap5.html"
        attrs = {"class": "table table-striped table-hover table-sm"}
        fields = ("article", "amount", "price_without_vat", "vat",
                  "price_with_vat", "total_price_with_vat", "change")

    @staticmethod
    def render_amount(value, record):
        return f'{value} {record.unit}'

    @staticmethod
    def render_price_without_vat(value):
        return f'{intcomma(value)} Kč'

    @staticmethod
    def render_price_with_vat(value):
        return f'{intcomma(value)} Kč'

    @staticmethod
    def render_total_price_with_vat(value):
        return f'{intcomma(value)} Kč'
