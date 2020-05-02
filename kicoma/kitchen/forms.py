from django import forms

class RecipeSearchForm(forms.Form):
    name = forms.CharField()


class StockReceiptSearchForm(forms.Form):
    createdAt = forms.CharField()
    userCreated__name = forms.CharField()
