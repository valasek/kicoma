#!/usr/bin/env python
import csv
import json
import sys
from datetime import datetime, timezone

migrationComment = 'Strávníček - testovací data'

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


def transformIngredientRecordJSON(inputRow, pk):
    # recipe, article, amount , unit
    # cislo, sklpol, norma,
    now = datetime.now(timezone.utc)
    outputRow = {
        "model": "kitchen.ingredient",
        "pk": pk,
        "fields": {
            'created': now.strftime("%Y-%m-%d %H:%M-0100"),
            'modified': now.strftime("%Y-%m-%d %H:%M-0100"),
            'recipe': inputRow[0],
            'article': inputRow[1],
            'amount': inputRow[2],
            'unit': checkUnit(inputRow, 3)
        }
    }
    return outputRow


def transformArticleRecordJSON(inputRow, pk=0):
    # ['sklpol', 'název ', 'jednotka', 'koeficient', 'nasklade', 'celkcena', 'alergeny']
    # id, article, onStock, averagePrice, unit, comment, allergen
    inputRow = cleanRow(inputRow)
    now = datetime.now(timezone.utc)
    outputRow = {
        "model": "kitchen.article",
        "pk": int(inputRow[0]),
        "fields": {
            'created': now.strftime("%Y-%m-%d %H:%M-0100"),
            'modified': now.strftime("%Y-%m-%d %H:%M-0100"),
            'article': inputRow[1],
            'onStock': 0,
            'averagePrice': 0,
            'unit': checkUnit(inputRow, 2),
            'allergen': transformAllergen(inputRow[6]),
            'comment': migrationComment
        }
    }
    return outputRow


def transformRecipeRecordJSON(inputRow, pk=0):
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
    return outputRow


def transformJSON(fileIn, fileOut, folder, rowFnc):
    pathFileIn = folder + fileIn
    pathFileOut = folder + fileOut
    inputFile = csv.reader(open(pathFileIn, 'r'))
    rowNumber = 1
    data = []
    for row in inputFile:
        if rowNumber == 1:
            rowNumber += 1
            continue
        data.append(rowFnc(row, rowNumber))
        rowNumber += 1
    with open(pathFileOut, 'w') as outputFile:
        outputFile.write(json.dumps(data, indent=2))
    print(f'{rowFnc.__name__} transformed {rowNumber} rows')


def main():
    folder = '/home/valasek/Programming/kima/kicoma/kicoma/kitchen/fixtures/'
    if sys.argv[1] == 'article':
        transformJSON('sklad-in.csv', 'article.json', folder, transformArticleRecordJSON)
    if sys.argv[1] == 'recipe':
        transformJSON('recepty-in.csv', 'recipe.json', folder, transformRecipeRecordJSON)
    if sys.argv[1] == 'ingredient':
        transformJSON('ingredience-in.csv', 'ingredient.json', folder, transformIngredientRecordJSON)
    if sys.argv[1] == 'all':
        transformJSON('sklad-in.csv', 'article.json', folder, transformArticleRecordJSON)
        transformJSON('recepty-in.csv', 'recipe.json', folder, transformRecipeRecordJSON)
        transformJSON('ingredience-in.csv', 'ingredient.json', folder, transformIngredientRecordJSON)


if __name__ == "__main__":
    main()
