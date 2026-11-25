from decimal import Decimal

from src.core.errors import ApiError
from src.core.utils import num, to_money
from src.core.audit import audit
from products.models import CATEGORIES, MAX_MONEY
from products.repository import (
    add_product,
    delete_product,
    get_product,
    hide_product,
    list_products,
    name_exists,
    product_is_used,
    update_product,
)


def clean_text(value, label: str, max_len: int = 45) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApiError(422, f"{label} is required.")
    if len(text) > max_len:
        raise ApiError(422, f"{label} is too long ({max_len} characters max).")
    return text


def clean_money(value, label: str) -> Decimal:
    amount = to_money(value, label)
    if amount < 0:
        raise ApiError(422, f"{label} can't be negative.")
    if amount > MAX_MONEY:
        raise ApiError(422, f"{label} is too large.")
    return amount


def clean_category(value) -> str:
    if value not in CATEGORIES:
        raise ApiError(422, "Category must be Coffee, Non-Coffee or Refreshers.")
    return value


def serialize_product(row: dict) -> dict:
    return {
        "id": row["productid"],
        "name": row["productname"],
        "category": row["category"],
        "price": num(row["sellingprice"]),
        "packagingCost": num(row["packagingcost"]),
        "cost": num(row["productcost"]),
        "available": row["isavailable"],
    }


def get_product_response(cur, product_id: int) -> dict:
    row = get_product(cur, product_id)
    if not row:
        raise ApiError(404, "Product not found.")
    return serialize_product(row)


def list_product_response(cur, available: bool | None = None) -> list[dict]:
    return [serialize_product(row) for row in list_products(cur, available)]


def check_name_free(cur, name: str, ignore_id: int | None = None) -> None:
    if name_exists(cur, name, ignore_id):
        raise ApiError(409, f"There is already a product named {name}.")


def add_product_service(cur, user: dict, body: dict | None) -> tuple[dict, int]:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    name = clean_text(body.get("name"), "Product name")
    category = clean_category(body.get("category"))
    price = clean_money(body.get("price"), "Selling price")
    packaging = clean_money(body.get("packagingCost", 0), "Packaging cost")
    available = bool(body.get("available", True))
    check_name_free(cur, name)
    product_id = add_product(cur, name, category, price, packaging, available)
    audit(cur, user["userid"], f"Added product {name}", "PRODUCT", product_id)
    return get_product_response(cur, product_id), 201


def update_product_service(cur, user: dict, product_id: int, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    current = get_product_response(cur, product_id)
    name = clean_text(body["name"], "Product name") if "name" in body else current["name"]
    category = clean_category(body["category"]) if "category" in body else current["category"]
    price = clean_money(body["price"], "Selling price") if "price" in body else Decimal(str(current["price"]))
    packaging = clean_money(body["packagingCost"], "Packaging cost") if "packagingCost" in body else Decimal(str(current["packagingCost"]))
    available = bool(body["available"]) if "available" in body else current["available"]
    check_name_free(cur, name, product_id)
    update_product(cur, product_id, name, category, price, packaging, available)
    audit(cur, user["userid"], f"Updated product {name}", "PRODUCT", product_id)
    return get_product_response(cur, product_id)


def delete_product_service(cur, user: dict, product_id: int) -> dict:
    product = get_product_response(cur, product_id)
    if product_is_used(cur, product_id):
        hide_product(cur, product_id)
        audit(cur, user["userid"], f"Marked product {product['name']} unavailable", "PRODUCT", product_id)
        return {"deleted": False, "product": get_product_response(cur, product_id)}
    delete_product(cur, product_id)
    audit(cur, user["userid"], f"Deleted product {product['name']}", "PRODUCT", product_id)
    return {"deleted": True, "product": None}
