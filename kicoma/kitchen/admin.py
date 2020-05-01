from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from django.contrib import admin
from . models import Unit, StockReceipt, StockIssue, Item, Allergen, MealType, Recipe, \
                     Ingredient, TargetGroup, VAT, DailyMenu, Article

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


class TargetGroupResource(resources.ModelResource):

    class Meta:
        model = TargetGroup
        skip_unchanged = True
        report_skipped = True


class UnitResource(resources.ModelResource):

    class Meta:
        model = Unit
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
    list_display = ('percentage', 'name',)
    ordering = ('-percentage',)
    resource_class = VATResource


class UnitAdmin(ImportExportActionModelAdmin):
    list_display = ('name',)
    ordering = ('name',)
    resource_class = UnitResource


class TargetGroupAdmin(ImportExportActionModelAdmin):
    list_display = ('name',)
    ordering = ('name',)
    resource_class = TargetGroupResource


class MealTypeAdmin(ImportExportActionModelAdmin):
    list_display = ('name',)
    ordering = ('name',)
    resource_class = MealTypeResource


class DailyMenuAdmin(ImportExportActionModelAdmin):
    list_display = ('date', 'amount', 'targetGroup', 'mealType', 'recipe')
    # ordering = ('category',)
    resource_class = DailyMenuResource


class ItemAdmin(ImportExportActionModelAdmin):
    list_display = ('stockIssue', 'stockReceipt', 'article', 'amount',
                    'unit', 'priceWithoutVat', 'vat', 'priceWithVat', 'comment', )
    fields = [('stockIssue', 'stockReceipt'),
              ('article', 'amount', 'unit'),
              ('priceWithoutVat', 'vat', 'priceWithVat'),
              'comment', ]
    # list_filter = ('unit', 'coefficient')
    # search_fields = ('name',)
    resource_class = ItemResource


class StockIssueAdmin(ImportExportActionModelAdmin):
    list_display = ('createdAt', 'userCreated', 'approved', 'approvedDate', 'userApproved',
                    'dailyMenu', 'comment', )
    fields = [('createdAt', 'userCreated', 'dailyMenu'), ('approved', 'approvedDate', 'userApproved'),
              'comment', ]
    resource_class = StockIssueResource


class StockReceiptAdmin(ImportExportActionModelAdmin):
    list_display = ('createdAt', 'userCreated', 'comment', )
    fields = [('createdAt', 'userCreated'), 'comment', ]
    resource_class = StockReceiptResource


class ArticleAdmin(ImportExportActionModelAdmin):
    list_display = ('code', 'name', 'unit', 'onStock', 'averagePrice', 'normPrice', 'display_allergens', 'comment', )
    fields = [('code', 'name', 'unit'), ('onStock', 'averagePrice', 'normPrice'), 'allergen', 'comment', ]
    # list_filter = ('unit', 'coefficient')
    search_fields = ('name',)
    resource_class = ArticleResource


class RecipeAdmin(ImportExportActionModelAdmin):
    list_display = ('name', 'norm_amount', 'comment')
    fields = ([('name', 'norm_amount'), 'comment'])
    resource_class = RecipeResource


class IngredientAdmin(ImportExportActionModelAdmin):
    list_display = ('recipe', 'article', 'amount', 'unit',)
    fields = [('recipe', 'article', 'amount', 'unit',)]
    resource_class = IngredientResource


admin.site.register(Allergen, AllergenAdmin)
admin.site.register(VAT, VATAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(TargetGroup, TargetGroupAdmin)
admin.site.register(MealType, MealTypeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(DailyMenu, DailyMenuAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(StockReceipt, StockReceiptAdmin)
admin.site.register(StockIssue, StockIssueAdmin)
admin.site.register(Item, ItemAdmin)
