from import_export import resources, widgets, fields
from import_export.admin import ImportExportActionModelAdmin
from django.contrib import admin
from . models import StockReceipt, StockIssue, StockIssueArticle, StockReceiptArticle, Allergen, MealType, Recipe, \
    RecipeArticle, MealGroup, VAT, Menu, MenuRecipe, DailyMenu, Article, DailyMenuRecipe

# create import export resources


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
    on_stock = fields.Field(widget=widgets.DecimalWidget(coerce_to_string=False))
    min_on_stock = fields.Field(widget=widgets.DecimalWidget(coerce_to_string=False))
    total_price = fields.Field(widget=widgets.DecimalWidget(coerce_to_string=False))
    # on_stock = models.DecimalField(
    #     decimal_places=2, max_digits=8,
    #     default=0, verbose_name='Na skladu', help_text='Celkové množství zboží na skladu')
    # min_on_stock = models.DecimalField(
    #     decimal_places=2, max_digits=8, blank=True, validators=[MinValueValidator(Decimal('0'))],
    #     default=0, verbose_name='Minimálně na skladu', help_text='Minimální množství zboží na skladu')
    # total_price = models.DecimalField(
    #     max_digits=8, blank=True, null=True, decimal_places=2,
    #     default=0, verbose_name='Celková cena s DPH', help_text='Celková cena zboží na skladu')


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


class VATAdmin(ImportExportActionModelAdmin):
    list_display = ('percentage', 'rate',)
    ordering = ('-percentage',)
    resource_class = VATResource


class AllergenAdmin(ImportExportActionModelAdmin):
    list_display = ('code', 'description',)
    ordering = ('code',)
    resource_class = AllergenResource


class MealGroupAdmin(ImportExportActionModelAdmin):
    list_display = ('meal_group',)
    ordering = ('meal_group',)
    resource_class = MealGroupResource


class MealTypeAdmin(ImportExportActionModelAdmin):
    list_display = ('meal_type',)
    ordering = ('meal_type',)
    resource_class = MealTypeResource


class ArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('article', 'unit', 'on_stock', 'min_on_stock',
                    'total_price', 'display_allergens', 'comment', )
    fields = [('article', 'unit'),
              ('on_stock', 'min_on_stock', 'total_price'),
              'allergen', 'comment', ]
    # list_filter = ('unit', 'coefficient')
    search_fields = ('article',)
    resource_class = ArticleResource


class RecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'norm_amount', 'procedure', 'comment')
    fields = ([('recipe', 'norm_amount'), ('comment', 'procedure')])
    resource_class = RecipeResource


class RecipeArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'article', 'amount', 'unit', 'comment',)
    fields = [('recipe', 'article', 'amount', 'unit', 'comment')]
    resource_class = RecipeArticleResource


class MenuAdmin(ImportExportActionModelAdmin):
    list_display = ('menu', 'meal_type', 'comment')
    resource_class = MenuResource


class MenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('menu', 'recipe', 'amount')
    resource_class = MenuRecipeResource


class DailyMenuAdmin(ImportExportActionModelAdmin):
    list_display = ('date', 'menu', 'meal_group', 'meal_type', 'comment')
    resource_class = DailyMenuResource


class DailyMenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('daily_menu', 'amount', 'recipe', 'comment')
    resource_class = DailyMenuRecipeResource


class StockIssueAdmin(ImportExportActionModelAdmin):
    list_display = ('user_created', 'approved', 'date_approved', 'user_approved',
                    'comment', )
    fields = [('user_created', ), ('approved', 'date_approved', 'user_approved'),
              'comment', ]
    resource_class = StockIssueResource


class StockReceiptAdmin(ImportExportActionModelAdmin):
    list_display = ('user_created', 'approved', 'date_approved', 'user_approved',
                    'comment', )
    fields = [('user_created', ), ('approved', 'date_approved', 'user_approved'),
              'comment', ]
    resource_class = StockReceiptResource


class StockIssueArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('stock_issue', 'article', 'amount',
                    'unit', 'average_unit_price', 'comment', )
    fields = [('stock_issue', 'article', 'amount'),
              ('average_unit_price', 'unit'),
              'comment', ]
    resource_class = StockIssueArticleResource


class StockReceiptArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('stock_receipt', 'article', 'amount',
                    'unit', 'price_without_vat', 'vat', 'comment', )
    fields = [('stock_receipt', 'article', 'amount'),
              ('unit', 'price_without_vat', 'vat'),
              'comment', ]
    resource_class = StockReceiptArticleResource


admin.site.register(Allergen, AllergenAdmin)
admin.site.register(VAT, VATAdmin)
admin.site.register(MealGroup, MealGroupAdmin)
admin.site.register(MealType, MealTypeAdmin)
admin.site.register(RecipeArticle, RecipeArticleAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Menu, MenuAdmin)
admin.site.register(MenuRecipe, MenuRecipeAdmin)
admin.site.register(DailyMenu, DailyMenuAdmin)
admin.site.register(DailyMenuRecipe, DailyMenuRecipeAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(StockReceipt, StockReceiptAdmin)
admin.site.register(StockIssue, StockIssueAdmin)
admin.site.register(StockIssueArticle, StockIssueArticleAdmin)
admin.site.register(StockReceiptArticle, StockReceiptArticleAdmin)
