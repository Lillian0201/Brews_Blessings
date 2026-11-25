from typing import TypedDict


SALE_STATUSES = ("Completed", "Refunded", "Voided")
WHOLE_ORDER = "Whole order"


class SaleRow(TypedDict, total=False):
    orderid: int
    ordernumber: str
    customername: str
    orderdatetime: object
    totalamount: object
    orderstatus: str
