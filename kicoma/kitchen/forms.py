from django import forms
# from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import StockReceipt, Item, Ingredient


class RecipeSearchForm(forms.Form):
    recipe = forms.CharField()


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        exclude = ()


class ArticleSearchForm(forms.Form):
    article = forms.CharField()


class StockReceiptSearchForm(forms.Form):
    dateCreated = forms.CharField()
    userCreated__name = forms.CharField()


class StockReceiptItemSearchForm(forms.Form):
    article__article = forms.CharField()


class DailyMenuSearchForm(forms.Form):
    date = forms.CharField()


class StockReceiptItemForm(forms.ModelForm):

    class Meta:
        model = Item
        exclude = ["stockIssue"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('amount', css_class='col-md-1'),
                Column('unit', css_class='col-md-1'),
                # Column(AppendedText('priceWithoutVat', 'Kč', active=True), css_class='col-md-2'),
                Column('priceWithoutVat', css_class='col-md-1'),
                Column('vat', css_class='col-md-2'),
                Column('comment', css_class='col-md-4'),
            )
        )


class StockReceiptForm(forms.ModelForm):
    # dateCreated = forms.DateField(widget=forms.DateInput(
    #     attrs={'type': 'date'}), initial=datetime.date.today, label='Datum vytvoření')

    class Meta:
        model = StockReceipt
        exclude = ["userCreated"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.disable_csrf = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        # self.helper.template = 'bootstrap/table_inline_formset.html'
        self.helper.layout = Layout(
            Row(
                Column('dateCreated', css_class='col-md-2'),
                Column('comment', css_class='col-md-10')
            )
        )

