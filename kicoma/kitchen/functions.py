from django.forms import ValidationError


# convert item amount or price between units, units are defined in .models.UNIT
def convertUnits(number, unitIn, unitOut):
    if unitIn == unitOut:
        return number
    if unitIn == 'kg' and unitOut == 'g':
        return number*1000
    if unitIn == 'g' and unitOut == 'kg':
        return number/1000
    if unitIn == 'l' and unitOut == 'ml':
        return number*100
    if unitIn == 'ml' and unitOut == 'l':
        return number/100
    print('ERROR: chyba konverze', number, unitIn, unitOut)
    raise ValidationError("Nedokáži provést {} konverzi {} na {}".format(number, unitIn, unitOut))


# returns total Item price, Item amount is converted using Article unit
def totalStockItemPrice(items):
    totalPrice = 0
    for item in items:
        convertedAmount = convertUnits(item.amount, item.unit, item.article.unit)
        itemPrice = convertedAmount * item.price_with_vat
        print("totalStockItemPrice: item, itemPrice, convertedAmount, item.price_with_vat\n",
              item, itemPrice, convertedAmount, item.price_with_vat)
        totalPrice += itemPrice
    return totalPrice

# returns total Ingredient price, Ingedient amount is converted using Article unit
def totalIngredientPrice(items):
    totalPrice = 0
    for item in items:
        convertedAmount = convertUnits(item.amount, item.unit, item.article.unit)
        itemPrice = convertedAmount * item.article.averagePrice
        print("totalIngredientPrice: item, itemPrice, convertedAmount, item.article.averagePrice\n",
              item, itemPrice, convertedAmount, item.article.averagePrice)
        totalPrice += itemPrice
    return totalPrice
