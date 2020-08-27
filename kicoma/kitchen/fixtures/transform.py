#!/usr/bin/env python
import json
import sys
from datetime import datetime
import pytz

folder = '/home/valasek/Programming/kima/kicoma/kicoma/kitchen/fixtures/'
recipeInFile = 'in/Recipe.json'
recipeInFilePath = folder + recipeInFile
articleInFile = 'in/Article.json'
articleInFilePath = folder + articleInFile
recipe_articleInFile = 'in/RecipeArticle.json'
recipe_articleInFilePath = folder + recipe_articleInFile
dailyMenuInFile = 'in/DailyMenu.json'
dailyMenuInFilePath = folder + dailyMenuInFile


def transformAllergen(allergen):
    if allergen == "":
        return []
    else:
        return allergen.split(",")


def transformRecipeArticleRecordJSON(inputRecord):
    created = pytz.utc.localize(datetime.strptime(
        inputRecord['created'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    modified = pytz.utc.localize(datetime.strptime(
        inputRecord['modified'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    outputRecord = {
        "model": "kitchen.recipearticle",
        "pk": inputRecord['id'],
        "fields": {
            'created': created,
            'modified': modified,
            'recipe': inputRecord['recipe'],
            'article': inputRecord['article'],
            'amount': inputRecord['amount'],
            'unit': inputRecord['unit'],
            'comment': inputRecord['comment']
        }
    }
    return outputRecord


def transformArticleRecordJSON(inputRecord):
    created = pytz.utc.localize(datetime.strptime(
        inputRecord['created'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    modified = pytz.utc.localize(datetime.strptime(
        inputRecord['modified'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")

    outputRecord = {
        "model": "kitchen.article",
        "pk": inputRecord['id'],
        "fields": {
            'created': created,
            'modified': modified,
            'article': inputRecord['article'],
            'unit': inputRecord['unit'],
            'on_stock': inputRecord['on_stock'],
            'min_on_stock': inputRecord['min_on_stock'],
            'total_price': inputRecord['total_price'],
            'allergen': transformAllergen(inputRecord['allergen']),
            'comment': inputRecord['comment']
        }
    }
    return outputRecord


def transformRecipeRecordJSON(inputRecord):
    created = pytz.utc.localize(datetime.strptime(
        inputRecord['created'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    modified = pytz.utc.localize(datetime.strptime(
        inputRecord['modified'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    outputRecord = {
        "model": "kitchen.recipe",
        "pk": inputRecord['id'],
        "fields": {
            'created': created,
            'modified': modified,
            'recipe': inputRecord['recipe'],
            'norm_amount': inputRecord['norm_amount'],
            'procedure': inputRecord['procedure'],
            'comment': inputRecord['comment']
        }
    }
    return outputRecord


def transformDailyMenuRecordJSON(inputRecord):
    created = pytz.utc.localize(datetime.strptime(
        inputRecord['created'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    modified = pytz.utc.localize(datetime.strptime(
        inputRecord['modified'], "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S%z")
    outputRecord = {
        "model": "kitchen.dailymenu",
        "pk": inputRecord['id'],
        "fields": {
            'created': created,
            'modified': modified,
            'date': inputRecord['date'],
            'meal_group': inputRecord['meal_group'],
            'meal_type': inputRecord['meal_type'],
            'comment': inputRecord['comment']
        }
    }
    return outputRecord


def transformJSON(fileInPath, fileOut, rowFnc):
    pathFileOut = folder + fileOut
    with open(fileInPath, 'r') as f:
        inputData = json.load(f)
    recordNumber = 0
    data = []
    for record in inputData:
        outputRecord = rowFnc(record)
        if outputRecord != {}:
            data.append(outputRecord)
        else:
            print("skipping")
        recordNumber += 1
    with open(pathFileOut, 'w') as outputFile:
        outputFile.write(json.dumps(data, indent=2))
    print(f'{rowFnc.__name__} transformed {recordNumber} records')


def main():
    if len(sys.argv) != 2:
        print("Usage: /transform.py article|recipe|recipe_article|all")
        exit()
    if sys.argv[1] == 'article':
        transformJSON(articleInFilePath, 'article.json', transformArticleRecordJSON)
    if sys.argv[1] == 'recipe':
        transformJSON(recipeInFilePath, 'recipe.json', transformRecipeRecordJSON)
    if sys.argv[1] == 'recipe_article':
        transformJSON(recipe_articleInFilePath, 'recipe_article.json', transformRecipeArticleRecordJSON)
    if sys.argv[1] == 'daily_menu':
        transformJSON(dailyMenuInFilePath, 'daily_menu.json', transformDailyMenuRecordJSON)
    if sys.argv[1] == 'all':
        transformJSON(articleInFilePath, 'article.json', transformArticleRecordJSON)
        transformJSON(recipeInFilePath, 'recipe.json', transformRecipeRecordJSON)
        transformJSON(recipe_articleInFilePath, 'recipe_article.json', transformRecipeArticleRecordJSON,)
        transformJSON(dailyMenuInFilePath, 'daily_menu.json', transformDailyMenuRecordJSON)


if __name__ == "__main__":
    main()
