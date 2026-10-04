"""Functions used for"""

from decimal import ROUND_HALF_UP, Decimal

from django.contrib.humanize.templatetags.humanize import intcomma
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

UNIT_PRICE_QUANTUM = Decimal("0.0001")
DISPLAY_PRICE_QUANTUM = Decimal("0.01")


def quantize_unit_price(value):
    return Decimal(value).quantize(UNIT_PRICE_QUANTUM)


# prices are stored with 4 decimal places but always shown with 2
def format_unit_price(value):
    if value is None or value == "":
        return ""
    return intcomma(
        Decimal(str(value)).quantize(DISPLAY_PRICE_QUANTUM, rounding=ROUND_HALF_UP)
    )


# convert article amount or price between units, units are defined in .models.UNIT
def convert_units(number, unit_in, unit_out):
    if unit_in == unit_out:
        return number
    if unit_in == "kg" and unit_out == "g":
        return number * 1000
    if unit_in == "g" and unit_out == "kg":
        return number / 1000
    if unit_in == "l" and unit_out == "ml":
        return number * 1000
    if unit_in == "ml" and unit_out == "l":
        return number / 1000
    raise ValidationError(
        _("Není možné provést konverzi {number} {unit_in} na {unit_out}").format(
            number=number, unit_in=unit_in, unit_out=unit_out
        )
    )
