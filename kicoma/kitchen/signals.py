# from django.db.models.signals import post_save
# from django.dispatch import receiver
from .models import Article
from .functions import convertUnits


# # update Article amount - based on units
# # instance - Item object being saved
# @receiver(post_save, sender=Item, dispatch_uid="my_unique_identifier")
# def save_item(sender, instance, *args, **kwargs):
#     article = Article.objects.filter(pk=instance.article.id).values_list('onStock', 'unit')
#     onStock = article[0][0]
#     stockUnit = article[0][1]
#     itemUnit = instance.unit
#     if instance.stockReceipt is not None and instance.stockIssue is None:
#         Article.objects.filter(pk=instance.article.id).update(
#             onStock=onStock + convertUnits(instance.amount, itemUnit, stockUnit))
#         print("1", onStock, convertUnits(instance.amount, itemUnit, stockUnit), itemUnit, stockUnit)
#     else:
#         if instance.stockReceipt is None and instance.stockIssue is not None:
#             Article.objects.filter(pk=instance.article.id).update(
#                 onStock=onStock - convertUnits(instance.amount, itemUnit, stockUnit))
#             print("2", onStock, convertUnits(instance.amount, itemUnit, stockUnit), itemUnit, stockUnit)
#         else:
#             raise Exception(
#                 "Item is not linked to StockReceipt or StockIssue or linked to both. Only one should be populated.")

def updateOnStock(article_id, stock_direction, new_amount, old_amount, new_unit):
    """When the stock receipt or issue is created or updated, stock amount has to be altered"""
    article = Article.objects.filter(pk=article_id).values_list('onStock', 'unit')
    onStock = article[0][0]
    old_unit = article[0][1]
    if stock_direction == 'receipt':
        Article.objects.filter(pk=article_id).update(
            onStock=onStock + convertUnits(new_amount - old_amount, new_unit, old_unit))
        print("Prijemka",
              article_id, stock_direction, onStock, new_amount, old_amount, new_unit, old_unit,
              convertUnits(new_amount - old_amount, new_unit, old_unit))
    else:
        if stock_direction == 'issue':
            Article.objects.filter(pk=article_id).update(
                onStock=onStock - convertUnits(new_amount - old_amount, new_unit, old_unit))
            print("Vydejka",
                  article_id, stock_direction, onStock, new_amount, old_amount, new_unit, old_unit,
                  convertUnits(new_amount - old_amount, new_unit, old_unit))
        else:
            raise Exception(
                "Item is not linked to StockReceipt or StockIssue or linked to both. Only one should be populated.")


def updateTotalPrice(article_id, stock_direction, price_with_vat):
    """When the stock receipt or issue is created or updated, totalPrice has to be altered"""
    article = Article.objects.filter(pk=article_id).values_list('totalPrice')
    oldTotalPrice = article[0][0]
    if stock_direction == 'receipt':
        Article.objects.filter(pk=article_id).update(totalPrice=oldTotalPrice + price_with_vat)
        print("Prijemka", article_id, stock_direction, price_with_vat, oldTotalPrice)
    else:
        if stock_direction == 'issue':
            Article.objects.filter(pk=article_id).update(totalPrice=oldTotalPrice - price_with_vat)
            print("Vydejka", article_id, stock_direction, price_with_vat, oldTotalPrice)
        else:
            raise Exception(
                "Item is not linked to StockReceipt or StockIssue or linked to both. Only one should be populated.")
