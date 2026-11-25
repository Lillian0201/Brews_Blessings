from decimal import Decimal
from typing import TypedDict


EXPENSE_TYPES = (
    "Rent", "Electricity", "Water", "Internet", "Salaries/Wages", "Supplies",
    "Operating Transportation Expenses", "Maintenance", "Other Expenses",
)
MAX_AMOUNT = Decimal("99999999.99")


class ExpenseRow(TypedDict, total=False):
    expenseid: int
    expensedate: object
    expensetype: str
    description: str
    amount: Decimal
    recordedby: str
