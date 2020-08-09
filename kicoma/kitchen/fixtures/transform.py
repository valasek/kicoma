#!/usr/bin/env python
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

migrationComment = ''

allergenReplacer = {
    '1a': '2',
    '1b': '3',
    '1c': '4',
    '1d': '5',
    '3': '10',
    '4': '11',
    '6': '13',
    '7': '14',
    '8a': '16',
    '8c': '18',
    '9': '24',
    '10': '25',
    '12': '27',
    '13': '28',
}

folder = '/home/valasek/Programming/kima/kicoma/kicoma/kitchen/fixtures/'
recipeInFile = 'recepty-in.csv'
recipeInFilePath = folder + recipeInFile
articleInFile = 'sklad-in.csv'
articleInFilePath = folder + articleInFile
recipe_articleInFile = 'ingredience-in.csv'
recipe_articleInFilePath = folder + recipe_articleInFile


def transformAllergen(origIng):
    inIng = origIng.lower().split(',')
    outIng = [allergenReplacer.get(item, item) for item in inIng]
    if len(inIng) != len(outIng):
        print(f'allergen transformation error from {inIng} to {outIng}')
    if outIng[0] == '':
        return []
    return outIng


def checkUnit(unit, index):
    u = unit[index].lower()
    if u in ('kg', 'g', 'ks', 'l'):
        return u.lower()
    print(f'unit {u} not allowed and removed {unit}')
    return ''


def cleanRow(row):
    row[6] = row[6].replace('.', ',')
    return row


def checkIfIsImported(value, importedList, name):
    if value in importedList:
        # print(value, "found in", name)
        return True
    # print(value, "not found in", name)
    return False


def returnImported():
    recipeColumns = defaultdict(list)
    with open(recipeInFilePath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for (k, v) in row.items():
                recipeColumns[k].append(v)
    articleColumns = defaultdict(list)
    with open(articleInFilePath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for (k, v) in row.items():
                articleColumns[k].append(v)
    return recipeColumns['cislo'], articleColumns['sklpol']


def transformRecipeArticleRecordJSON(inputRow, **kwargs):
    # recipe, article, amount , unit
    # cislo	sklpol	název	norma	jednotka
    now = datetime.now(timezone.utc)
    importedRecipes, importedArticles = returnImported()
    if checkIfIsImported(inputRow[0], importedRecipes, 'recipes'):
        if checkIfIsImported(inputRow[1], importedArticles, 'articles'):
            outputRow = {
                "model": "kitchen.recipearticle",
                "pk": kwargs['pk'],
                "fields": {
                    'created': now.strftime("%Y-%m-%d %H:%M-0100"),
                    'modified': now.strftime("%Y-%m-%d %H:%M-0100"),
                    'recipe': inputRow[0],  # recipe
                    'article': inputRow[1],  # article
                    'amount': inputRow[3],  # amount
                    'unit': checkUnit(inputRow, 4)  # unit
                }
            }
        else:
            # print(
            #     "Skipped - recipe id: {} is not in imported, not able to create a parent relationship".format(inputRow[0]))
            kwargs['skippedRecipes'] += + 1
            return {}, kwargs
    else:
        # print(
        #     "Skipped - Stock article id: {} is not in imported, not able to create a parent relationship".format(inputRow[1]))
        kwargs['skippedArticles'] += 1
        return {}, kwargs

    return outputRow, kwargs


def transformArticleRecordJSON(inputRow, **kwargs):
    # ['sklpol', 'název ', 'jednotka', 'koeficient', 'nasklade', 'celkcena', 'alergeny']
    # id, article, on_stock, average_price, unit, comment, allergen
    inputRow = cleanRow(inputRow)
    now = datetime.now(timezone.utc)
    outputRow = {
        "model": "kitchen.article",
        "pk": int(inputRow[0]),
        "fields": {
            'created': now.strftime("%Y-%m-%d %H:%M-0100"),
            'modified': now.strftime("%Y-%m-%d %H:%M-0100"),
            'article': inputRow[1],
            'on_stock': 0,
            'unit': checkUnit(inputRow, 2),
            'allergen': transformAllergen(inputRow[6]),
            'comment': migrationComment
        }
    }
    return outputRow, kwargs


def transformRecipeRecordJSON(inputRow, **kwargs):
    # id, recipe, norm_amount, procedure
    # cislo, JMENO, energie, normstr
    now = datetime.now(timezone.utc)
    outputRow = {
        "model": "kitchen.recipe",
        "pk": int(inputRow[0]),
        "fields": {
            'created': now.strftime("%Y-%m-%d %H:%M-0100"),
            'modified': now.strftime("%Y-%m-%d %H:%M-0100"),
            'recipe': inputRow[1],
            'norm_amount': inputRow[3]
        }
    }
    return outputRow, kwargs


def transformJSON(fileInPath, fileOut, rowFnc, **kwargs):
    pathFileOut = folder + fileOut
    inputFile = csv.reader(open(fileInPath, 'r'))
    rowNumber = 1
    data = []
    skippedRecords = 0
    currentSkippedRecipes = 0
    currentSkippedArticles = 0
    for row in inputFile:
        if rowNumber == 1:
            rowNumber += 1
            continue
        outputRow, rkwargs = rowFnc(row,
                                    pk=rowNumber,
                                    skippedRecipes=kwargs['skippedRecipes'],
                                    skippedArticles=kwargs['skippedArticles'])
        if outputRow != {}:
            data.append(outputRow)
        else:
            skippedRecords += 1
        currentSkippedRecipes += rkwargs['skippedRecipes']
        currentSkippedArticles += rkwargs['skippedArticles']
        rowNumber += 1
    with open(pathFileOut, 'w') as outputFile:
        outputFile.write(json.dumps(data, indent=2))
    print(f'{rowFnc.__name__} transformed {rowNumber} rows, skipped {skippedRecords}')
    return currentSkippedRecipes, currentSkippedArticles


def main():
    skippedRecipes = 0
    skippedArticles = 0
    if sys.argv[1] == 'article':
        transformJSON(articleInFilePath, 'article.json', transformArticleRecordJSON)
    if sys.argv[1] == 'recipe':
        transformJSON(recipeInFilePath, 'recipe.json', transformRecipeRecordJSON)
    if sys.argv[1] == 'recipe_article':
        skippedRecipes, skippedArticles = transformJSON(recipe_articleInFilePath, 'recipe_article.json',
                                                        transformRecipeArticleRecordJSON,
                                                        skippedRecipes=skippedRecipes,
                                                        skippedArticles=skippedArticles)
        print("Skipped", skippedRecipes, "recipes and", skippedArticles, "articles.")
    if sys.argv[1] == 'all':
        transformJSON(articleInFilePath, 'article.json', transformArticleRecordJSON, skippedRecipes=skippedRecipes,
                      skippedArticles=skippedArticles)
        transformJSON(recipeInFilePath, 'recipe.json', transformRecipeRecordJSON, skippedRecipes=skippedRecipes,
                      skippedArticles=skippedArticles)
        skippedRecipes, skippedArticles = transformJSON(recipe_articleInFilePath, 'recipe_article.json',
                                                        transformRecipeArticleRecordJSON,
                                                        skippedRecipes=skippedRecipes,
                                                        skippedArticles=skippedArticles)
        print("Skipped", skippedRecipes, "recipes and", skippedArticles, "articles.")


if __name__ == "__main__":
    main()
