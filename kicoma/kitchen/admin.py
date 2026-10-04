from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
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

    def before_save_instance(self, instance, row, **kwargs):
        if (
            instance.pk
            and StockReceiptArticle.objects.filter(
                vat_id=instance.pk, stock_receipt__approved=True
            ).exists()
        ):
            old_percentage = VAT.objects.get(pk=instance.pk).percentage
            if old_percentage != instance.percentage:
                raise ValidationError(
                    _("Sazbu DPH použitou na schválené příjemce nelze změnit.")
                )
        super().before_save_instance(instance, row, **kwargs)


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

    def before_save_instance(self, instance, row, **kwargs):
        reject_approval_change(instance)
        super().before_save_instance(instance, row, **kwargs)

    def before_delete_instance(self, instance, row, **kwargs):
        reject_approval_change(instance, deleting=True)
        super().before_delete_instance(instance, row, **kwargs)


class StockReceiptResource(resources.ModelResource):
    class Meta:
        model = StockReceipt
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        reject_approval_change(instance)
        super().before_save_instance(instance, row, **kwargs)

    def before_delete_instance(self, instance, row, **kwargs):
        reject_approval_change(instance, deleting=True)
        super().before_delete_instance(instance, row, **kwargs)


def reject_approval_change(document, deleting=False):
    stored_approved = (
        type(document)
        .objects.filter(pk=document.pk)
        .values_list("approved", flat=True)
        .first()
        if document.pk
        else None
    )
    if stored_approved or (not deleting and document.approved):
        raise ValidationError(
            _("Schválený doklad nelze importem změnit ani smazat ({document}).").format(
                document=document
            )
        )


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
        widget=widgets.DecimalWidget(coerce_to_string=False),
    )
    min_on_stock = fields.Field(
        attribute="min_on_stock",
        column_name="min_on_stock",
        widget=widgets.DecimalWidget(coerce_to_string=False),
    )
    total_price = fields.Field(
        attribute="total_price",
        column_name="total_price",
        widget=widgets.DecimalWidget(coerce_to_string=False),
    )

    class Meta:
        model = Article
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        if instance.pk:
            old_unit = (
                Article.objects.filter(pk=instance.pk)
                .values_list("unit", flat=True)
                .first()
            )
            if old_unit is not None and old_unit != instance.unit:
                raise ValidationError(
                    _("{article}: jednotku nelze měnit ({old} -> {new}).").format(
                        article=instance.article, old=old_unit, new=instance.unit
                    )
                )
        super().before_save_instance(instance, row, **kwargs)


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

    def before_save_instance(self, instance, row, **kwargs):
        reject_approved_line_change(instance, "stock_issue")
        super().before_save_instance(instance, row, **kwargs)

    def before_delete_instance(self, instance, row, **kwargs):
        reject_approved_line_change(instance, "stock_issue")
        super().before_delete_instance(instance, row, **kwargs)


class StockReceiptArticleResource(resources.ModelResource):
    class Meta:
        model = StockReceiptArticle
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        reject_approved_line_change(instance, "stock_receipt")
        super().before_save_instance(instance, row, **kwargs)

    def before_delete_instance(self, instance, row, **kwargs):
        reject_approved_line_change(instance, "stock_receipt")
        super().before_delete_instance(instance, row, **kwargs)


def line_document_approved(line, document_field):
    """True when the line's new or stored document is approved."""
    model = type(line)
    document_ids = {getattr(line, f"{document_field}_id")}
    if line.pk:
        document_ids.add(
            model.objects.filter(pk=line.pk)
            .values_list(f"{document_field}_id", flat=True)
            .first()
        )
    document_model = model._meta.get_field(document_field).related_model
    return document_model.objects.filter(
        pk__in=[pk for pk in document_ids if pk], approved=True
    ).exists()


def reject_approved_line_change(line, document_field):
    if line_document_approved(line, document_field):
        raise ValidationError(
            _("Řádek schváleného dokladu nelze změnit ani smazat ({line}).").format(
                line=line
            )
        )


class ApprovedDocumentAdminMixin:
    """Approved receipts/issues and their lines are read-only, stock is not recalculated here."""

    document_field: str | None = None

    def is_approved(self, obj):
        if obj is None:
            return False
        if self.document_field is None:
            return bool(obj.approved)
        return line_document_approved(obj, self.document_field)

    def has_change_permission(self, request, obj=None):
        if self.is_approved(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if self.is_approved(obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_approved_filter(self):
        if self.document_field is None:
            return {"approved": True}
        return {f"{self.document_field}__approved": True}

    def delete_queryset(self, request, queryset):
        approved = queryset.filter(**self.get_approved_filter())
        if approved.exists():
            self.message_user(
                request,
                _("Schválené doklady a jejich řádky nebyly smazány: {count}").format(
                    count=approved.count()
                ),
                level=messages.WARNING,
            )
        super().delete_queryset(request, queryset.exclude(**self.get_approved_filter()))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        document_field = self.document_field
        if document_field is None or document_field not in form.base_fields:
            return form
        # a line cannot be added to an approved document
        form.base_fields[document_field].queryset = form.base_fields[
            document_field
        ].queryset.exclude(approved=True)
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if self.document_field is None:
            # approval only through the application, it changes the stock
            return (*readonly, "approved", "date_approved", "user_approved")
        return readonly


# integrate import/export into admin


@admin.register(AppSettings)
class AppSettingsAdmin(ImportExportActionModelAdmin):
    list_display = ("currency",)
    resource_class = AppSettingsResource


@admin.register(VAT)
class VATAdmin(ImportExportActionModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if (
            obj
            and StockReceiptArticle.objects.filter(
                vat=obj, stock_receipt__approved=True
            ).exists()
        ):
            return (*readonly, "percentage")
        return readonly

    list_display = (
        "percentage",
        "rate",
    )
    ordering = ("-percentage",)
    resource_class = VATResource


@admin.register(Allergen)
class AllergenAdmin(ImportExportActionModelAdmin):
    list_display = (
        "code",
        "description",
    )
    ordering = ("code",)
    resource_class = AllergenResource


@admin.register(MealGroup)
class MealGroupAdmin(ImportExportActionModelAdmin):
    list_display = ("meal_group",)
    ordering = ("meal_group",)
    resource_class = MealGroupResource


@admin.register(MealType)
class MealTypeAdmin(ImportExportActionModelAdmin):
    list_display = ("meal_type",)
    ordering = ("meal_type",)
    resource_class = MealTypeResource


@admin.register(Article)
class ArticleAdmin(ImportExportActionModelAdmin):
    list_display = (
        "article",
        "unit",
        "on_stock",
        "min_on_stock",
        "total_price",
        "display_allergens",
        "comment",
    )
    fields = [
        ("article", "unit"),
        ("on_stock", "min_on_stock", "total_price"),
        "allergen",
        "comment",
    ]
    # list_filter = ('unit', 'coefficient')
    search_fields = ("article",)
    resource_class = ArticleResource

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.pk:
            return (*super().get_readonly_fields(request, obj), "unit")
        return super().get_readonly_fields(request, obj)


@admin.register(Recipe)
class RecipeAdmin(ImportExportActionModelAdmin):
    list_display = ("recipe", "norm_amount", "procedure", "comment")
    fields = [("recipe", "norm_amount"), ("comment", "procedure")]
    resource_class = RecipeResource


@admin.register(RecipeArticle)
class RecipeArticleAdmin(ImportExportActionModelAdmin):
    list_display = (
        "recipe",
        "article",
        "amount",
        "unit",
        "comment",
    )
    fields = [("recipe", "article", "amount", "unit", "comment")]
    resource_class = RecipeArticleResource


@admin.register(Menu)
class MenuAdmin(ImportExportActionModelAdmin):
    list_display = ("menu", "meal_type", "comment")
    resource_class = MenuResource


@admin.register(MenuRecipe)
class MenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ("menu", "recipe", "amount")
    resource_class = MenuRecipeResource


@admin.register(DailyMenu)
class DailyMenuAdmin(ImportExportActionModelAdmin):
    list_display = ("date", "menu", "meal_group", "meal_type", "comment")
    resource_class = DailyMenuResource


@admin.register(DailyMenuRecipe)
class DailyMenuRecipeAdmin(ImportExportActionModelAdmin):
    list_display = ("daily_menu", "amount", "recipe", "comment")
    resource_class = DailyMenuRecipeResource


@admin.register(StockIssue)
class StockIssueAdmin(ApprovedDocumentAdminMixin, ImportExportActionModelAdmin):
    list_display = (
        "user_created",
        "approved",
        "date_approved",
        "user_approved",
        "comment",
    )
    fields = [
        ("user_created",),
        ("approved", "date_approved", "user_approved"),
        "comment",
    ]
    resource_class = StockIssueResource


@admin.register(StockReceipt)
class StockReceiptAdmin(ApprovedDocumentAdminMixin, ImportExportActionModelAdmin):
    list_display = (
        "user_created",
        "approved",
        "date_approved",
        "user_approved",
        "comment",
    )
    fields = [
        ("user_created",),
        ("approved", "date_approved", "user_approved"),
        "comment",
    ]
    resource_class = StockReceiptResource


@admin.register(StockIssueArticle)
class StockIssueArticleAdmin(ApprovedDocumentAdminMixin, ImportExportActionModelAdmin):
    document_field = "stock_issue"
    list_display = (
        "stock_issue",
        "article",
        "amount",
        "unit",
        "average_unit_price",
        "comment",
    )
    fields = [
        ("stock_issue", "article", "amount"),
        ("average_unit_price", "unit"),
        "comment",
    ]
    resource_class = StockIssueArticleResource


@admin.register(StockReceiptArticle)
class StockReceiptArticleAdmin(
    ApprovedDocumentAdminMixin, ImportExportActionModelAdmin
):
    document_field = "stock_receipt"
    list_display = (
        "stock_receipt",
        "article",
        "amount",
        "unit",
        "price_without_vat",
        "vat",
        "comment",
    )
    fields = [
        ("stock_receipt", "article", "amount"),
        ("unit", "price_without_vat", "vat"),
        "comment",
    ]
    resource_class = StockReceiptArticleResource
