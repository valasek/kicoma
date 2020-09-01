from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import StockReceipt, StockIssue, StockIssueArticle, StockReceiptArticle, RecipeArticle, \
    Article, Recipe, DailyMenu, DailyMenuRecipe


class ArticleForm(forms.ModelForm):

    class Meta:
        model = Article
        fields = ["article", "unit", "on_stock", "min_on_stock", "total_price", "comment", "allergen", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['on_stock'].widget.attrs['readonly'] = True
        self.fields['total_price'].widget.attrs['readonly'] = True
        # self.fields['averagePrice'].widget.attrs['readonly'] = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('unit', css_class='col-md-2'),
                Column('on_stock', css_class='col-md-2'),
                Column('min_on_stock', css_class='col-md-2'),
                Column('total_price', css_class='col-md-2'),
                # Column('averagePrice', css_class='col-md-2'),
            ),
            Row(
                Column('allergen', css_class='col-md-6'),
                Column('comment', css_class='col-md-6'),
            )
        )


class ArticleSearchForm(forms.Form):
    article = forms.CharField()


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
                Column('recipe', css_class='col-md-4'),
                Column('norm_amount', css_class='col-md-4'),
                Column('comment', css_class='col-md-4'),
            ),
            Row(
                Column('procedure', css_class='col-md-12'),
            )
        )


class RecipeSearchForm(forms.Form):
    recipe = forms.CharField()


class RecipeArticleForm(forms.ModelForm):

    class Meta:
        model = RecipeArticle
        fields = ["article", "amount", "unit", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-3'),
                Column('amount', css_class='col-md-3'),
                Column('unit', css_class='col-md-3'),
                Column('comment', css_class='col-md-3'),
            ),
        )


class DailyMenuForm(forms.ModelForm):

    class Meta:
        model = DailyMenu
        fields = ["date", "meal_group", "meal_type", "comment"]
        # widgets = {
        #     'date': forms.DateInput(format=('%Y-%m-%d'),
        #                             attrs={'class': 'form-control', 'placeholder': 'Select Date', 'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-2'),
                Column('meal_group', css_class='col-md-2'),
                Column('meal_type', css_class='col-md-2'),
                Column('comment', css_class='col-md-6'),
            )
        )


class DailyMenuSearchForm(forms.Form):
    date = forms.CharField()


class DailyMenuPrintForm(forms.ModelForm):

    class Meta:
        model = DailyMenu
        fields = ["date", "meal_group"]
        # widgets = {
        #     'date': forms.DateInput(format=('%Y-%m-%d'),
        #                             attrs={'class': 'form-control', 'placeholder': 'Select Date', 'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['meal_group'].required = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-2'),
                Column('meal_group', css_class='col-md-2'),
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
                Column('recipe', css_class='col-md-2'),
                Column('amount', css_class='col-md-2'),
                Column('comment', css_class='col-md-6'),
            )
        )


class StockIssueForm(forms.ModelForm):
    # dateCreated = forms.DateField(widget=forms.DateInput(
    #     attrs={'type': 'date'}), initial=datetime.date.today, label='Datum vytvoření')

    class Meta:
        model = StockIssue
        fields = ["comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.disable_csrf = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        # self.helper.template = 'bootstrap/table_inline_formset.html'
        self.helper.layout = Layout(
            Row(
                Column('comment', css_class='col-md-12')
            )
        )


class StockIssueSearchForm(forms.Form):
    approved = forms.BooleanField()
    created = forms.CharField()
    userApproved__name = forms.CharField()


class StockIssueFromDailyMenuForm(forms.ModelForm):

    class Meta:
        model = DailyMenu
        fields = ["date"]
        # widgets = {
        #     'date': forms.DateInput(format=('%Y-%m-%d'),
        #                             attrs={'class': 'form-control', 'placeholder': 'Select Date', 'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-2'),
            )
        )


class StockIssueArticleForm(forms.ModelForm):

    class Meta:
        model = StockIssueArticle
        fields = ["article", "amount", "unit", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('amount', css_class='col-md-1'),
                Column('unit', css_class='col-md-1'),
                Column('comment', css_class='col-md-4'),
            )
        )


class StockReceiptForm(forms.ModelForm):
    # dateCreated = forms.DateField(widget=forms.DateInput(
    #     attrs={'type': 'date'}), initial=datetime.date.today, label='Datum vytvoření')

    class Meta:
        model = StockReceipt
        fields = ["date_created", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['userCreated'].widget.attrs['readonly'] = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.disable_csrf = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        # self.helper.template = 'bootstrap/table_inline_formset.html'
        self.helper.layout = Layout(
            Row(
                Column('date_created', css_class='col-md-2'),
                Column('comment', css_class='col-md-10')
            )
        )


class StockReceiptSearchForm(forms.Form):
    created = forms.CharField()
    userCreated__name = forms.CharField()


class StockReceiptArticleForm(forms.ModelForm):

    class Meta:
        model = StockReceiptArticle
        fields = ["article", "amount", "unit", "price_without_vat", "vat", "comment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        # self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.layout = Layout(
            Row(
                Column('article', css_class='col-md-2'),
                Column('amount', css_class='col-md-1'),
                Column('unit', css_class='col-md-1'),
                Column('price_without_vat', css_class='col-md-2'),
                Column('vat', css_class='col-md-1'),
                Column('comment', css_class='col-md-4'),
            )
        )


class FoodConsumptionPrintForm(forms.ModelForm):

    class Meta:
        model = DailyMenu
        fields = ["date", "meal_group", ]
        # widgets = {
        #     'date': forms.DateInput(format=('%Y-%m-%d'),
        #                             attrs={'class': 'form-control', 'placeholder': 'Select Date', 'type': 'date'})
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['meal_group'].required = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-2'),
                Column('meal_group', css_class='col-md-2'),
            )
        )
