from typing import TypedDict


class DashboardRow(TypedDict, total=False):
    gross: object
    orders_today: int
    pending: int
    completed: int
    cancelled: int
