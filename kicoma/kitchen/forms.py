from django import forms

class RecipeBookSearchForm(forms.Form):
    code = forms.CharField()
    name = forms.CharField()
