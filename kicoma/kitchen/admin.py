from import_export import resources
from import_export.admin import ImportExportActionModelAdmin
from django.contrib import admin
from . models import Unit, Item, Allergen, MealType, RecipeBook, TargetGroup

# class PageAdmin(admin.ModelAdmin):
#     list_display = ('title', 'update_date')
#     ordering = ('title',)
#     search_fields = ('title',)

# admin.site.register(PageAdmin)

# create import export resources


class AllergenResource(resources.ModelResource):

    class Meta:
        model = Allergen
        skip_unchanged = True
        report_skipped = True


class ItemResource(resources.ModelResource):

    class Meta:
        model = Item
        skip_unchanged = True
        report_skipped = True


class RecipeBookResource(resources.ModelResource):

    class Meta:
        model = RecipeBook
        skip_unchanged = True
        report_skipped = True


class UnitResource(resources.ModelResource):

    class Meta:
        model = Unit
        skip_unchanged = True
        report_skipped = True

# integrate inport export into admin


class AllergenAdmin(ImportExportActionModelAdmin):
    resource_class = AllergenResource


class ItemAdmin(ImportExportActionModelAdmin):
    resource_class = ItemResource


class RecipeBookAdmin(ImportExportActionModelAdmin):
    resource_class = RecipeBookResource


class UnitAdmin(ImportExportActionModelAdmin):
    resource_class = UnitResource


admin.site.register(Unit, UnitAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Allergen, AllergenAdmin)
admin.site.register(MealType)
admin.site.register(RecipeBook, RecipeBookAdmin)
admin.site.register(TargetGroup)
