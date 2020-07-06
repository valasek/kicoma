from django.forms import ValidationError


# convert item amount between units, units are defined in .models.UNIT
def convertUnits(amount, unitIn, unitOut):
    if unitIn == unitOut:
        return amount
    if unitIn == 'kg' and unitOut == 'g':
        return amount*1000
    if unitIn == 'g' and unitOut == 'kg':
        return amount/1000
    if unitIn == 'l' and unitOut == 'ml':
        return amount*100
    if unitIn == 'ml' and unitOut == 'l':
        return amount/100
    print('ERROR: chyba konverze', amount, unitIn, unitOut)
    raise ValidationError("Nedokáži provést konverzi {} na {}".format(unitIn, unitOut))

# returns total Item/Ingredient price, Item/Ingedient amount is converted using Article unit
def totalItemPrice(items):
    totalPrice = 0
    for item in items:
        convertedAmount = convertUnits(item.amount, item.unit, item.article.unit)
        itemPrice = convertedAmount * item.article.averagePrice
        totalPrice += itemPrice
    return totalPrice
