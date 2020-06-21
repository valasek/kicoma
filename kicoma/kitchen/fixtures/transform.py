#!/usr/bin/env python
import csv
import sys

migrationComment = 'Přesunuto z Jídelníčku'

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
    return ','.join(outIng)


def checkUnit(unit,index):
    u = unit[index].lower()
    if u in ('kg', 'g', 'ks', 'l'):
        return u.lower()
    print(f'unit {u} not allowed and removed {unit}')
    return ''


def cleanRow(row):
    row[6] = row[6].replace('.', ',')
    return row


def transformArticleRecord(inputRow):
    # ['sklpol', 'název ', 'jednotka', 'koeficient', 'nasklade', 'celkcena', 'alergeny']
    # id, name, onStock, averagePrice, unit, comment, allergen
    inputRow = cleanRow(inputRow)
    outputRow = ['', '', '0', '0', '', migrationComment, '']
    outputRow[0] = inputRow[0]  # id
    outputRow[1] = inputRow[1]  # name
    outputRow[4] = checkUnit(inputRow,2)  # unit
    outputRow[6] = transformAllergen(inputRow[6])  # allergen
    return outputRow


def transformRecipeRecord(inputRow):
    # id, name, norm_amount, procedure
    # cislo, JMENO, energie, normstr
    outputRow = ['', '', '', migrationComment]
    outputRow[0] = inputRow[0]  # id
    outputRow[1] = inputRow[1]  # name
    outputRow[2] = inputRow[3]  # norm_amount
    return outputRow

def transformIngredientRecord(inputRow):
    # recipe, article, amount , unit
    # cislo, sklpol, norma, jednotka
    outputRow = ['', '', '', '']
    outputRow[0] = inputRow[0]  # recipe
    outputRow[1] = inputRow[1]  # article
    outputRow[2] = inputRow[2]  # amount
    outputRow[3] = checkUnit(inputRow,3)  # unit
    return outputRow


def transform(fileIn, fileOut, folder, rowFnc, header):
    skladFileIn = folder + fileIn
    skladFileOut = folder + fileOut
    inputFile = csv.reader(open(skladFileIn, 'r'))
    outputFile = open(skladFileOut, 'w')
    writer = csv.writer(outputFile)
    rowNumber = 1
    for row in inputFile:
        if rowNumber == 1:
            writer.writerow(header)
        else:
            writer.writerow(rowFnc(row))
        rowNumber += 1
    print(f'{rowFnc.__name__} transformed {rowNumber} rows')


def main():
    folder = '/home/valasek/Programming/kima/kicoma/kicoma/kitchen/fixtures/'
    if sys.argv[1] == 'article':
        transform('sklad-in.csv', 'article-in.csv', folder, transformArticleRecord,
                  ['id', 'name', 'onStock', 'averagePrice', 'unit', 'comment', 'allergen'])
    if sys.argv[1] == 'recipe':
        transform('recepty-in.csv', 'recipe-in.csv', folder, transformRecipeRecord,
                  ['id', 'name', 'norm_amount', 'procedure'])
    if sys.argv[1] == 'ingredient':
        transform('ingredience-in.csv', 'ingredient-in.csv', folder, transformIngredientRecord,
                  ['recipe', 'article', 'amount', 'unit'])
    if sys.argv[1] == 'all':
        transform('sklad-in.csv', 'article-in.csv', folder, transformArticleRecord,
                  ['id', 'name', 'onStock', 'averagePrice', 'unit', 'comment', 'allergen'])
        transform('recepty-in.csv', 'recipe-in.csv', folder, transformRecipeRecord,
                  ['id', 'name', 'norm_amount', 'procedure'])
        transform('ingredience-in.csv', 'ingredient-in.csv', folder, transformIngredientRecord,
                  ['recipe', 'article', 'amount', 'unit'])


if __name__ == "__main__":
    main()
