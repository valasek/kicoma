from django import forms

class RecipeSearchForm(forms.Form):
    name = forms.CharField()
