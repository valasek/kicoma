from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Item, Article
from .functions import convertUnits


# update Article amount - based on units
# instance - Item object being saved
@receiver(pre_save, sender=Item)
def save_item(sender, instance, *args, **kwargs):
    article = Article.objects.filter(pk=instance.article.id).values_list('onStock', 'unit')
    onStock = article[0][0]
    stockUnit = article[0][1]
    itemUnit = instance.unit
    if instance.stockReceipt is not None and instance.stockIssue is None:
        Article.objects.filter(pk=instance.article.id).update(
            onStock=onStock + convertUnits(instance.amount, itemUnit, stockUnit))
        print("1", onStock, convertUnits(instance.amount, itemUnit, stockUnit), itemUnit, stockUnit)
    else:
        if instance.stockReceipt is None and instance.stockIssue is not None:
            Article.objects.filter(pk=instance.article.id).update(
                onStock=onStock - convertUnits(instance.amount, itemUnit, stockUnit))
            print("2", onStock, convertUnits(instance.amount, itemUnit, stockUnit), itemUnit, stockUnit)
        else:
            raise Exception(
                "Item is not linked to StockReceipt or StockIssue or linked to both. Only one should be populated.")
