from django.forms import ValidationError

def convertUnits(amount, unitIn, unitOut):
    print(amount, unitIn, unitOut)
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
    raise ValidationError("Nedokáži provést konverzi {} na {}".format(unitIn, unitOut))
