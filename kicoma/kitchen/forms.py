from django import forms
# from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import StockReceipt, Item, Ingredient, Article, Recipe, DailyMenu


class RecipeSearchForm(forms.Form):
    recipe = forms.CharField()


class RecipeIngredientSearchForm(forms.Form):
    article = forms.CharField()


class RecipeForm(forms.ModelForm):

    class Meta:
        model = Recipe
        fields = ["recipe", "norm_amount", "procedure"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('recipe', css_class='col-md-6'),
                Column('norm_amount', css_class='col-md-6'),
                Column('comment', css_class='col-md-8'),
            ),
            Row(
                Column('procedure', css_class='col-md-12'),
            )
        )


class RecipeIngredientForm(forms.ModelForm):

    class Meta:
        model = Ingredient
        fields = ["article", "amount", "unit"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-3'),
                Column('amount', css_class='col-md-3'),
                Column('unit', css_class='col-md-3'),
            ),
        )


class ArticleForm(forms.ModelForm):

    class Meta:
        model = Article
        fields = ["article", "unit", "comment", "allergen", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('unit', css_class='col-md-2'),
                Column('comment', css_class='col-md-8'),
            ),
            Row(
                Column('allergen', css_class='col-md-12'),
            )
        )


class ArticleSearchForm(forms.Form):
    article = forms.CharField()


class StockReceiptSearchForm(forms.Form):
    created = forms.CharField()
    userCreated__name = forms.CharField()


class StockReceiptItemSearchForm(forms.Form):
    article__article = forms.CharField()


class DailyMenuSearchForm(forms.Form):
    date = forms.CharField()


class DailyMenuForm(forms.ModelForm):

    class Meta:
        model = DailyMenu
        fields = ["date", "amount", "mealGroup", "mealType", "recipe"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-2'),
                Column('amount', css_class='col-md-2'),
                Column('mealGroup', css_class='col-md-2'),
                Column('mealType', css_class='col-md-2'),
                Column('recipe', css_class='col-md-2'),
            ),
        )


class StockReceiptItemForm(forms.ModelForm):

    class Meta:
        model = Item
        exclude = ["stockIssue"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['priceWithoutVat'].required = True
        self.fields['vat'].required = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
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
                # Column('dateCreated', css_class='col-md-2'),
                Column('comment', css_class='col-md-12')
            )
        )
