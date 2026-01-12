from django.contrib import admin
from import_export import fields, resources, widgets
from import_export.admin import ImportExportActionModelAdmin

from .models import (
    VAT,
    Allergen,
    AppSettings,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
    MealType,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
)

# create import export resources

class AppSettingsResource(resources.ModelResource):

    class Meta:
        model = AppSettings
        skip_unchanged = True
        report_skipped = True


class VATResource(resources.ModelResource):

    class Meta:
        model = VAT
        skip_unchanged = True
        report_skipped = True


class AllergenResource(resources.ModelResource):

    class Meta:
        model = Allergen
        skip_unchanged = True
        report_skipped = True


class StockIssueResource(resources.ModelResource):

    class Meta:
        model = StockIssue
        skip_unchanged = True
        report_skipped = True


class StockReceiptResource(resources.ModelResource):

    class Meta:
        model = StockReceipt
        skip_unchanged = True
        report_skipped = True


class MealTypeResource(resources.ModelResource):

    class Meta:
        model = MealType
        skip_unchanged = True
        report_skipped = True


class MealGroupResource(resources.ModelResource):

    class Meta:
        model = MealGroup
        skip_unchanged = True
        report_skipped = True


class ArticleResource(resources.ModelResource):
    on_stock = fields.Field(
        attribute="on_stock",
        column_name="on_stock",
        widget=widgets.DecimalWidget(coerce_to_string=False)
    )
    min_on_stock = fields.Field(
        attribute="min_on_stock",
        column_name="min_on_stock",
        widget=widgets.DecimalWidget(coerce_to_string=False)
    )
    total_price = fields.Field(
        attribute="total_price",
        column_name="total_price",
        widget=widgets.DecimalWidget(coerce_to_string=False)
    )

    class Meta:
        model = Article
        skip_unchanged = True
        report_skipped = True


class MenuResource(resources.ModelResource):

    class Meta:
        model = Menu
        skip_unchanged = True
        report_skipped = True


class MenuRecipeResource(resources.ModelResource):

    class Meta:
        model = MenuRecipe
        skip_unchanged = True
        report_skipped = True


class DailyMenuResource(resources.ModelResource):

    class Meta:
        model = DailyMenu
        skip_unchanged = True
        report_skipped = True


class DailyMenuRecipeResource(resources.ModelResource):

    class Meta:
        model = DailyMenuRecipe
        skip_unchanged = True
        report_skipped = True


class RecipeResource(resources.ModelResource):

    class Meta:
        model = Recipe
        skip_unchanged = True
        report_skipped = True


class RecipeArticleResource(resources.ModelResource):

    class Meta:
        model = RecipeArticle
        skip_unchanged = True
        report_skipped = True


class StockIssueArticleResource(resources.ModelResource):

    class Meta:
        model = StockIssueArticle
        skip_unchanged = True
        report_skipped = True


class StockReceiptArticleResource(resources.ModelResource):

    class Meta:
        model = StockReceiptArticle
        skip_unchanged = True
        report_skipped = True

# integrate import/export into admin


@admin.register(AppSettings)
class AppSettingsAdmin(ImportExportActionModelAdmin):
    list_display = ('currency', )
    resource_class = AppSettingsResource


@admin.register(VAT)
class VATAdmin(ImportExportActionModelAdmin):
    list_display = ('percentage', 'rate',)
    ordering = ('-percentage',)
    resource_class = VATResource


@admin.register(Allergen)
class AllergenAdmin(ImportExportActionModelAdmin):
    list_display = ('code', 'description',)
    ordering = ('code',)
    resource_class = AllergenResource


@admin.register(MealGroup)
class MealGroupAdmin(ImportExportActionModelAdmin):
    list_display = ('meal_group',)
    ordering = ('meal_group',)
    resource_class = MealGroupResource


@admin.register(MealType)
class MealTypeAdmin(ImportExportActionModelAdmin):
    list_display = ('meal_type',)
    ordering = ('meal_type',)
    resource_class = MealTypeResource


@admin.register(Article)
class ArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('article', 'unit', 'on_stock', 'min_on_stock',
                    'total_price', 'display_allergens', 'comment', )
    fields = [('article', 'unit'),
              ('on_stock', 'min_on_stock', 'total_price'),
              'allergen', 'comment', ]
    # list_filter = ('unit', 'coefficient')
    search_fields = ('article',)
    resource_class = ArticleResource


@admin.register(Recipe)
class RecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'norm_amount', 'procedure', 'comment')
    fields = ([('recipe', 'norm_amount'), ('comment', 'procedure')])
    resource_class = RecipeResource


@admin.register(RecipeArticle)
class RecipeArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'article', 'amount', 'unit', 'comment',)
    fields = [('recipe', 'article', 'amount', 'unit', 'comment')]
    resource_class = RecipeArticleResource


@admin.register(Menu)
class MenuAdmin(ImportExportActionModelAdmin):
    list_display = ('menu', 'meal_type', 'comment')
    resource_class = MenuResource


@admin.register(MenuRecipe)
class MenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('menu', 'recipe', 'amount')
    resource_class = MenuRecipeResource


@admin.register(DailyMenu)
class DailyMenuAdmin(ImportExportActionModelAdmin):
    list_display = ('date', 'menu', 'meal_group', 'meal_type', 'comment')
    resource_class = DailyMenuResource


@admin.register(DailyMenuRecipe)
class DailyMenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('daily_menu', 'amount', 'recipe', 'comment')
    resource_class = DailyMenuRecipeResource


@admin.register(StockIssue)
class StockIssueAdmin(ImportExportActionModelAdmin):
    list_display = ('user_created', 'approved', 'date_approved', 'user_approved',
                    'comment', )
    fields = [('user_created', ), ('approved', 'date_approved', 'user_approved'),
              'comment', ]
    resource_class = StockIssueResource


@admin.register(StockReceipt)
class StockReceiptAdmin(ImportExportActionModelAdmin):
    list_display = ('user_created', 'approved', 'date_approved', 'user_approved',
                    'comment', )
    fields = [('user_created', ), ('approved', 'date_approved', 'user_approved'),
              'comment', ]
    resource_class = StockReceiptResource


@admin.register(StockIssueArticle)
class StockIssueArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('stock_issue', 'article', 'amount',
                    'unit', 'average_unit_price', 'comment', )
    fields = [('stock_issue', 'article', 'amount'),
              ('average_unit_price', 'unit'),
              'comment', ]
    resource_class = StockIssueArticleResource


@admin.register(StockReceiptArticle)
class StockReceiptArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('stock_receipt', 'article', 'amount',
                    'unit', 'price_without_vat', 'vat', 'comment', )
    fields = [('stock_receipt', 'article', 'amount'),
              ('unit', 'price_without_vat', 'vat'),
              'comment', ]
    resource_class = StockReceiptArticleResource


