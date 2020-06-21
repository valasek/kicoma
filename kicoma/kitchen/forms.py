from django import forms
from django.forms import BaseInlineFormSet
from django.forms.models import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import StockReceipt, Item, Recipe, Ingredient


class RecipeSearchForm(forms.Form):
    recipe = forms.CharField()


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        exclude = ()


IngredientFormSet = inlineformset_factory(
    Recipe, Ingredient, form=IngredientForm,
    fields=["article", "amount", "unit"],
    extra=4, can_delete=True
)


class ArticleSearchForm(forms.Form):
    article = forms.CharField()


class StockReceiptSearchForm(forms.Form):
    dateCreated = forms.CharField()
    userCreated__name = forms.CharField()


class DailyMenuSearchForm(forms.Form):
    date = forms.CharField()


class StockReceiptForm(forms.ModelForm):

    class Meta:
        model = StockReceipt
        exclude = ["userCreated"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = False
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        # self.helper.template = 'bootstrap/table_inline_formset.html'
        self.helper.layout = Layout(
            Row(
                Column('dateCreated', css_class='col-md-2'),
                Column('comment', css_class='col-md-10')
            )
        )


class BaseStockReceiptForm(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = False
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('amount', css_class='col-md-1'),
                Column('unit', css_class='col-md-1'),
                Column('priceWithoutVat', css_class='col-md-1'),
                Column('vat', css_class='col-md-2'),
                Column('comment', css_class='col-md-4'),
                Column('DELETE', css_class='col-md-1 d-flex align-items-center')
            )
        )
        self.helper.add_input(Submit("submit", "Uložit a aktualizovat skladové zásoby", css_class='btn-primary'))


# BaseModelFormSet
StockReceiptFormSet = inlineformset_factory(
    StockReceipt, Item, form=StockReceiptForm, formset=BaseStockReceiptForm,
    fields=["article", "amount", "unit", "priceWithoutVat", "vat", "comment"],
    extra=2, can_delete=True
)
