from typing import TypedDict


STATUSES = ("Pending", "Completed", "Cancelled")
ORDER_COLUMNS = ("orderid, ordernumber, customername, totalamount, discountamount, "
                 "paymentmethod, amounttendered, orderstatus, orderdatetime, cancelreason")


class OrderRow(TypedDict, total=False):
    orderid: int
    ordernumber: str
    customername: str
    totalamount: object
    discountamount: object
    paymentmethod: str
    amounttendered: object
    orderstatus: str
    orderdatetime: object
    cancelreason: str | None
