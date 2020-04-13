from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from django.contrib import admin
from . models import StockUnit, StockItem, Allergen, MealType, RecipeBook, TargetGroup

# create import export resources


class AllergenResource(resources.ModelResource):

    class Meta:
        model = Allergen
        skip_unchanged = True
        report_skipped = True


class StockItemResource(resources.ModelResource):

    class Meta:
        model = StockItem
        skip_unchanged = True
        report_skipped = True


class MealTypeResource(resources.ModelResource):

    class Meta:
        model = MealType
        skip_unchanged = True
        report_skipped = True


class RecipeBookResource(resources.ModelResource):

    class Meta:
        model = RecipeBook
        skip_unchanged = True
        report_skipped = True


class TargetGroupResource(resources.ModelResource):

    class Meta:
        model = TargetGroup
        skip_unchanged = True
        report_skipped = True


class StockUnitResource(resources.ModelResource):

    class Meta:
        model = StockUnit
        skip_unchanged = True
        report_skipped = True

# integrate inport export into admin


class AllergenAdmin(ImportExportActionModelAdmin):
    resource_class = AllergenResource


class StockItemAdmin(ImportExportActionModelAdmin):
    list_display = ('code', 'name', 'unit', 'coefficient', 'in_stock', 'cena_normy', 'display_allergens',)
    fields = [('code', 'name', 'unit'), ('coefficient', 'in_stock', 'cena_normy'), 'allergen', ]
    list_filter = ('unit', 'coefficient')
    ordering = ('code',)
    search_fields = ('code', 'name')
    resource_class = StockItemResource


class MealTypeAdmin(ImportExportActionModelAdmin):
    resource_class = MealTypeResource


class RecipeBookAdmin(ImportExportActionModelAdmin):
    resource_class = RecipeBookResource


class TargetGroupAdmin(ImportExportActionModelAdmin):
    resource_class = TargetGroupResource


class StockUnitAdmin(ImportExportActionModelAdmin):
    resource_class = StockUnitResource


admin.site.register(StockUnit, StockUnitAdmin)
admin.site.register(StockItem, StockItemAdmin)
admin.site.register(Allergen, AllergenAdmin)
admin.site.register(MealType, MealTypeAdmin)
admin.site.register(RecipeBook, RecipeBookAdmin)
admin.site.register(TargetGroup, TargetGroupAdmin)
