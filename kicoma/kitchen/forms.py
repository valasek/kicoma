from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row
from django import forms
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from .models import (
    NUTRITION_FIELDS,
    NUTRITION_STRUCTURE,
    UNIT,
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
from .unit_change import (
    article_unit_changed_since,
    latest_unit_change_id,
    recipe_unit_changed_since,
    unit_factor,
)


class FlatpickrDateInput(forms.DateInput):
    """Reusable Flatpickr-enabled DateInput widget."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].update(
            {
                "class": "form-control flatpickr-input",
                "placeholder": "YYYY-MM-DD",
            }
        )
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(*args, **kwargs)


class ArticleForm(forms.ModelForm):
    common_fields = (
        "article",
        "unit",
        "comment",
        "allergen",
    )
    stock_fields = (
        "on_stock",
        "min_on_stock",
        "total_price",
    )
    nutrition_fields = NUTRITION_FIELDS
    piece_fields = ("piece_weight", "piece_weight_unit")

    class Meta:
        model = Article
        fields = [
            "article",
            "unit",
            "on_stock",
            "min_on_stock",
            "total_price",
            *NUTRITION_FIELDS,
            "piece_weight",
            "piece_weight_unit",
            "comment",
            "allergen",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        group_names = set()
        if user is not None:
            group_names = set(user.groups.values_list("name", flat=True))
            if user.is_superuser:
                group_names.update(("stockkeeper", "nutrition_advisor"))

        editable_fields = set(self.common_fields)
        if "stockkeeper" in group_names:
            editable_fields.update(self.stock_fields)
        if "nutrition_advisor" in group_names:
            editable_fields.update(self.nutrition_fields)
            # piece weight only matters for ks; the unit of a new article is not known yet
            if not self.instance.pk or self.instance.unit == "ks":
                editable_fields.update(self.piece_fields)
        for field_name in tuple(self.fields):
            if field_name not in editable_fields:
                self.fields.pop(field_name)
        if self.instance.pk and "unit" in self.fields:
            self.fields["unit"].disabled = True
            self.fields["unit"].help_text = _(
                "Jednotku změníš pomocí tlačítka „Změnit jednotku“."
            )
            self.fields["unit_change_marker"] = forms.IntegerField(
                widget=forms.HiddenInput,
                required=False,
                min_value=0,
                initial=latest_unit_change_id(),
            )

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.render_hidden_fields = True
        main_columns = [
            Column("article", css_class="col-md-2"),
            Column("unit", css_class="col-md-2"),
        ]
        if "stockkeeper" in group_names:
            main_columns.extend(
                Column(field_name, css_class="col-md-2")
                for field_name in self.stock_fields
            )
        layout = [
            Row(*main_columns),
            Row(
                Column("allergen", css_class="col-md-6"),
                Column("comment", css_class="col-md-6"),
            ),
        ]
        if "nutrition_advisor" in group_names:
            nutrition_groups = Row(
                *(
                    Column(
                        Div(
                            parent_name,
                            css_class="nutrition-form__parent",
                        ),
                        Div(
                            *child_names,
                            css_class="nutrition-form__children",
                        ),
                        css_class="col-xl-6 nutrition-form__group",
                    )
                    for parent_name, child_names in NUTRITION_STRUCTURE
                    if child_names
                ),
                css_class="g-4",
            )
            nutrition_summary = Row(
                *(
                    Column(field_name, css_class="col-md-4")
                    for field_name, child_names in NUTRITION_STRUCTURE
                    if not child_names
                ),
                css_class="nutrition-form__summary",
            )
            layout.append(
                Fieldset(
                    _("Výživové údaje"),
                    nutrition_summary,
                    nutrition_groups,
                    *(
                        [
                            Row(
                                *(
                                    Column(field_name, css_class="col-md-3")
                                    for field_name in self.piece_fields
                                )
                            )
                        ]
                        if "piece_weight" in self.fields
                        else []
                    ),
                    css_class="nutrition-form",
                )
            )
        self.helper.layout = Layout(*layout)

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and article_unit_changed_since(
            self.instance, cleaned_data.get("unit_change_marker") or 0
        ):
            raise forms.ValidationError(
                _(
                    "Jednotka zboží se mezitím změnila. Obnov stránku a zadej změny znovu."
                )
            )
        # stock fields are blank=True but NOT NULL, an empty input must fall back to the model default
        for field_name in self.stock_fields:
            if field_name in cleaned_data and cleaned_data[field_name] is None:
                cleaned_data[field_name] = Article._meta.get_field(
                    field_name
                ).get_default()
        if "piece_weight" in self.fields:
            self.clean_piece_weight_fields(cleaned_data)
        return cleaned_data

    def clean_piece_weight_fields(self, cleaned_data):
        weight = cleaned_data.get("piece_weight")
        weight_unit = cleaned_data.get("piece_weight_unit")
        unit = cleaned_data.get("unit") or self.instance.unit
        has_nutrition = any(
            cleaned_data.get(field_name) for field_name in NUTRITION_FIELDS
        )
        required = bool(weight or weight_unit) or (unit == "ks" and has_nutrition)
        if not required:
            return
        message = _("Zboží v ks s výživovými údaji potřebuje hmotnost kusu i jednotku.")
        if not weight:
            self.add_error("piece_weight", message)
        if not weight_unit:
            self.add_error("piece_weight_unit", message)


class ArticleSearchForm(forms.Form):
    article = forms.CharField()


class StockArticlesExportForm(forms.Form):
    date = forms.DateField(label="Datum", widget=FlatpickrDateInput())

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value > localdate():
            raise forms.ValidationError(_("Datum nemůže být v budoucnosti."))
        return value


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["recipe", "norm_amount", "comment", "procedure"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("recipe", css_class="col-md-4"),
                Column("norm_amount", css_class="col-md-4"),
                Column("comment", css_class="col-md-4"),
            ),
            Row(
                Column("procedure", css_class="col-md-12"),
            ),
        )


class RecipeSearchForm(forms.Form):
    recipe = forms.CharField()


class UnitChangeGuardedForm(forms.ModelForm):
    """Reject a line whose units changed after the form was rendered."""

    marker_field = "unit_change_marker"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.marker_field] = forms.IntegerField(
            widget=forms.HiddenInput,
            required=False,
            min_value=0,
            initial=latest_unit_change_id(),
        )

    def clean(self):
        cleaned_data = super().clean()
        article = cleaned_data.get("article")
        marker = cleaned_data.get(self.marker_field) or 0
        stale_recipe = isinstance(
            self.instance, RecipeArticle
        ) and recipe_unit_changed_since(self.instance, marker)
        if article is not None and (
            article_unit_changed_since(article, marker) or stale_recipe
        ):
            data = self.data.copy()
            data[self.add_prefix(self.marker_field)] = latest_unit_change_id()
            for field_name in ("amount", "unit", "price_without_vat"):
                if field_name in self.fields:
                    data[self.add_prefix(field_name)] = ""
            self.data = data
            raise forms.ValidationError(
                _(
                    "Jednotka zboží {article} se mezitím změnila na {unit}, "
                    "zadej řádek znovu."
                ).format(article=article, unit=article.unit)
            )
        return cleaned_data


class RecipeArticleForm(UnitChangeGuardedForm):
    class Meta:
        model = RecipeArticle
        fields = ["article", "amount", "unit", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.render_hidden_fields = True
        self.helper.layout = Layout(
            Row(
                Column("article", css_class="col-md-3"),
                Column("amount", css_class="col-md-3"),
                Column("unit", css_class="col-md-3"),
                Column("comment", css_class="col-md-3"),
            ),
        )


class DailyMenuCreateForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ["date", "menu", "meal_group", "meal_type", "comment"]
        widgets = {"date": FlatpickrDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date", css_class="col-md-2"),
                Column("menu", css_class="col-md-2"),
                Column("meal_group", css_class="col-md-2"),
                Column("meal_type", css_class="col-md-2"),
                Column("comment", css_class="col-md-4"),
            )
        )


class DailyMenuEditForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ["date", "meal_group", "meal_type", "comment"]
        widgets = {"date": FlatpickrDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date", css_class="col-md-2"),
                Column("meal_group", css_class="col-md-2"),
                Column("meal_type", css_class="col-md-2"),
                Column("comment", css_class="col-md-4"),
            )
        )


class DailyMenuPrintForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ["date", "meal_group"]
        widgets = {"date": FlatpickrDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["meal_group"].required = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date", css_class="col-md-2"),
                Column("meal_group", css_class="col-md-2"),
            )
        )


class DailyMenuCateringUnitForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ["date"]
        widgets = {"date": FlatpickrDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date", css_class="col-md-3"),
            )
        )


class DailyMenuRecipeForm(forms.ModelForm):
    class Meta:
        model = DailyMenuRecipe
        fields = ["recipe", "amount", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("recipe", css_class="col-md-2"),
                Column("amount", css_class="col-md-2"),
                Column("comment", css_class="col-md-6"),
            )
        )

    def clean_recipe(self):
        # daily_menu is not a form field, so the unique_dailymenu_recipe_pair
        # constraint is skipped by ModelForm validation and has to be checked here
        recipe = self.cleaned_data["recipe"]
        daily_menu_id = self.instance.daily_menu_id
        if daily_menu_id is None:
            return recipe
        duplicates = DailyMenuRecipe.objects.filter(
            daily_menu_id=daily_menu_id, recipe=recipe
        ).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                _("Tento recept již v denním menu je, uprav počet porcí.")
            )
        return recipe


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ["menu", "meal_type", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("menu", css_class="col-md-2"),
                Column("meal_type", css_class="col-md-2"),
                Column("comment", css_class="col-md-6"),
            )
        )


class MenuRecipeForm(forms.ModelForm):
    class Meta:
        model = MenuRecipe
        fields = ["recipe", "amount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("recipe", css_class="col-md-2"),
                Column("amount", css_class="col-md-2"),
            )
        )

    def clean_recipe(self):
        # menu is not a form field, so the unique_menu_recipe_pair constraint
        # is skipped by ModelForm validation and has to be checked here
        recipe = self.cleaned_data["recipe"]
        menu_id = self.instance.menu_id
        if menu_id is None:
            return recipe
        duplicates = MenuRecipe.objects.filter(menu_id=menu_id, recipe=recipe).exclude(
            pk=self.instance.pk
        )
        if duplicates.exists():
            raise forms.ValidationError(
                _("Tento recept již v menu je, uprav počet porcí.")
            )
        return recipe


class StockIssueForm(forms.ModelForm):
    class Meta:
        model = StockIssue
        fields = ["comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Row(Column("comment", css_class="col-md-12")))


class StockIssueSearchForm(forms.Form):
    approved = forms.BooleanField()
    created = forms.DateField()
    userApproved__name = forms.CharField()


class StockIssueFromDailyMenuForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ["date"]
        widgets = {"date": FlatpickrDateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date", css_class="col-md-2"),
            )
        )


class ArticleUnitSelect(forms.Select):
    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if hasattr(value, "instance"):
            option["attrs"]["data-unit"] = value.instance.unit
        return option


class ArticleWithUnitChoiceField(forms.ModelChoiceField):
    widget = ArticleUnitSelect

    def label_from_instance(self, obj):
        return f"{obj.article} [{obj.get_unit_display()}]"


class StockIssueArticleForm(UnitChangeGuardedForm):
    class Meta:
        model = StockIssueArticle
        fields = ["article", "amount", "unit", "comment"]
        field_classes = {"article": ArticleWithUnitChoiceField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.render_hidden_fields = True
        self.helper.layout = Layout(
            Row(
                Column("article", css_class="col-md-2"),
                Column("amount", css_class="col-md-2"),
                Column("unit", css_class="col-md-2"),
                Column("comment", css_class="col-md-4"),
            )
        )


class StockReceiptForm(forms.ModelForm):
    class Meta:
        model = StockReceipt
        fields = ["date_created", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("date_created", css_class="col-md-2"),
                Column("comment", css_class="col-md-10"),
            )
        )


class StockReceiptSearchForm(forms.Form):
    created = forms.DateField()
    userCreated__name = forms.CharField()


class StockReceiptArticleForm(UnitChangeGuardedForm):
    class Meta:
        model = StockReceiptArticle
        fields = ["article", "amount", "unit", "price_without_vat", "vat", "comment"]
        field_classes = {"article": ArticleWithUnitChoiceField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.render_hidden_fields = True
        self.helper.layout = Layout(
            Row(
                Column("article", css_class="col-md-2"),
                Column("amount", css_class="col-md-2"),
                Column("unit", css_class="col-md-2"),
                Column("price_without_vat", css_class="col-md-2"),
                Column("vat", css_class="col-md-2"),
                Column("comment", css_class="col-md-2"),
            )
        )


class UnitChangeForm(forms.Form):
    new_unit = forms.ChoiceField(label=_("Nová jednotka"))
    factor = forms.DecimalField(
        required=False,
        localize=True,
        label=_("Převodní koeficient"),
        help_text=_("Pro kg ↔ g a l ↔ ml se doplní automaticky."),
    )
    source_note = forms.CharField(
        max_length=200,
        label=_("Zdroj koeficientu"),
        help_text=_("Např. „etiketa 42 g“ nebo „zváženo 10 ks = 420 g“."),
    )
    confirmed = forms.BooleanField(
        required=False,
        label=_("Varování jsem zkontroloval a výsledek beru na sebe."),
    )
    fingerprint = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, old_unit, unit_choices, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_unit = old_unit
        new_unit_field = self.fields["new_unit"]
        assert isinstance(new_unit_field, forms.ChoiceField)
        new_unit_field.choices = [
            (unit, label)
            for unit, label in UNIT
            if unit in unit_choices and unit != old_unit
        ]
        self.fields["factor"].label = _(
            "Koeficient: 1 {unit} = ? nové jednotky"
        ).format(unit=old_unit)

    def clean(self):
        cleaned_data = super().clean()
        new_unit = cleaned_data.get("new_unit")
        if not new_unit:
            return cleaned_data
        fixed, locked = unit_factor(self.old_unit, new_unit)
        if locked:
            cleaned_data["factor"] = fixed
        elif cleaned_data.get("factor") is None:
            self.add_error("factor", _("Zadej převodní koeficient."))
        elif cleaned_data["factor"] <= 0:
            self.add_error("factor", _("Koeficient musí být větší než 0."))
        return cleaned_data
