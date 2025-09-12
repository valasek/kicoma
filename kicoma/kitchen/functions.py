""" Functions used for """
from django.forms import ValidationError


# convert article amount or price between units, units are defined in .models.UNIT
def convert_units(number, unit_in, unit_out):
    if unit_in == unit_out:
        return number
    if unit_in == 'kg' and unit_out == 'g':
        return number*1000
    if unit_in == 'g' and unit_out == 'kg':
        return number/1000
    if unit_in == 'l' and unit_out == 'ml':
        return number*1000
    if unit_in == 'ml' and unit_out == 'l':
        return number/1000
    raise ValidationError(f"Není možné provést konverzi {number} {unit_in} na {unit_out}")


# returns total RecipeArticle price, RecipeArticle amount is converted using Article unit
def total_recipe_article_price(recipe_articles, norm_amount):
    total_price = 0
    for recipe_article in recipe_articles:
        converted_amount = convert_units(recipe_article.amount, recipe_article.unit, recipe_article.article.unit)
        recipe_article_price = converted_amount * recipe_article.average_unit_price * norm_amount
        total_price += recipe_article_price
    return total_price
