from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from django.contrib import admin
from . models import StockReceipt, StockIssue, Item, Allergen, MealType, Recipe, \
    Ingredient, MealGroup, VAT, DailyMenu, Article

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


class ItemResource(resources.ModelResource):

    class Meta:
        model = Item
        skip_unchanged = True
        report_skipped = True


class MealTypeResource(resources.ModelResource):

    class Meta:
        model = MealType
        skip_unchanged = True
        report_skipped = True


class DailyMenuResource(resources.ModelResource):

    class Meta:
        model = DailyMenu
        skip_unchanged = True
        report_skipped = True


class RecipeResource(resources.ModelResource):

    class Meta:
        model = Recipe
        skip_unchanged = True
        report_skipped = True


class IngredientResource(resources.ModelResource):

    class Meta:
        model = Ingredient
        skip_unchanged = True
        report_skipped = True


class MealGroupResource(resources.ModelResource):

    class Meta:
        model = MealGroup
        skip_unchanged = True
        report_skipped = True


class ArticleResource(resources.ModelResource):

    class Meta:
        model = Article
        skip_unchanged = True
        report_skipped = True

# integrate import/export into admin


class AllergenAdmin(ImportExportActionModelAdmin):
    list_display = ('code', 'description',)
    ordering = ('code',)
    resource_class = AllergenResource


class VATAdmin(ImportExportActionModelAdmin):
    list_display = ('percentage', 'rate',)
    ordering = ('-percentage',)
    resource_class = VATResource


class MealGroupAdmin(ImportExportActionModelAdmin):
    list_display = ('mealGroup',)
    ordering = ('mealGroup',)
    resource_class = MealGroupResource


class MealTypeAdmin(ImportExportActionModelAdmin):
    list_display = ('mealType',)
    ordering = ('mealType',)
    resource_class = MealTypeResource


class DailyMenuAdmin(ImportExportActionModelAdmin):
    list_display = ('date', 'amount', 'mealGroup', 'mealType', 'recipe')
    # ordering = ('category',)
    resource_class = DailyMenuResource


class ItemAdmin(ImportExportActionModelAdmin):
    list_display = ('stockIssue', 'stockReceipt', 'article', 'amount',
                    'unit', 'priceWithoutVat', 'vat', 'comment', )
    fields = [('stockIssue', 'stockReceipt'),
              ('article', 'amount', 'unit'),
              ('priceWithoutVat', 'vat'),
              'comment', ]
    # list_filter = ('unit', 'coefficient')
    # search_fields = ('name',)
    resource_class = ItemResource


class StockIssueAdmin(ImportExportActionModelAdmin):
    list_display = ('dateCreated', 'userCreated', 'approved', 'dateApproved', 'userApproved',
                    'dailyMenu', 'comment', )
    fields = [('dateCreated', 'userCreated', 'dailyMenu'), ('approved', 'dateApproved', 'userApproved'),
              'comment', ]
    resource_class = StockIssueResource


class StockReceiptAdmin(ImportExportActionModelAdmin):
    list_display = ('dateCreated', 'userCreated', 'comment', )
    fields = [('dateCreated', 'userCreated'), 'comment', ]
    resource_class = StockReceiptResource


class ArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('article', 'unit', 'onStock', 'averagePrice', 'display_allergens', 'comment', )
    fields = [('article', 'unit'), ('onStock', 'averagePrice'), 'allergen', 'comment', ]
    # list_filter = ('unit', 'coefficient')
    search_fields = ('name',)
    resource_class = ArticleResource


class RecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'norm_amount', 'procedure')
    fields = ([('recipe', 'norm_amount'), 'procedure'])
    resource_class = RecipeResource


class IngredientAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'article', 'amount', 'unit',)
    fields = [('recipe', 'article', 'amount', 'unit',)]
    resource_class = IngredientResource


admin.site.register(Allergen, AllergenAdmin)
admin.site.register(VAT, VATAdmin)
admin.site.register(MealGroup, MealGroupAdmin)
admin.site.register(MealType, MealTypeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(DailyMenu, DailyMenuAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(StockReceipt, StockReceiptAdmin)
admin.site.register(StockIssue, StockIssueAdmin)
admin.site.register(Item, ItemAdmin)
