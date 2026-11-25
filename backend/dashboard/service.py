from src.core.utils import num
from dashboard.repository import (
    best_sellers,
    dashboard_totals,
    stock_counts,
    today_expenses,
    today_refunds,
)


def dashboard_summary(cur) -> dict:
    totals = dashboard_totals(cur)
    refunds = today_refunds(cur)
    expenses = today_expenses(cur)
    best = [
        {"name": row["itemname"], "qty": num(row["qty"]), "sales": num(row["sales"])}
        for row in best_sellers(cur)
    ]
    stock = stock_counts(cur)
    gross = num(totals["gross"])
    refund_total = num(refunds)
    return {
        "todaySales": gross,
        "refunds": refund_total,
        "netSales": gross - refund_total,
        "ordersToday": totals["orders_today"],
        "pending": totals["pending"],
        "completed": totals["completed"],
        "cancelled": totals["cancelled"],
        "expensesToday": num(expenses),
        "bestSellers": best,
        "availableStock": stock["available"],
        "lowStock": stock["low"],
        "outOfStock": stock["out"],
        "stockAlerts": stock["low"] + stock["out"],
    }
