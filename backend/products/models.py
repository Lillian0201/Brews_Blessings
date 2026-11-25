from decimal import Decimal
from typing import TypedDict


CATEGORIES = ("Coffee", "Non-Coffee", "Refreshers")
MAX_MONEY = Decimal("99999999.99")


class ProductRow(TypedDict, total=False):
    productid: int
    productname: str
    category: str
    sellingprice: Decimal
    productcost: Decimal
    packagingcost: Decimal
    isavailable: bool
