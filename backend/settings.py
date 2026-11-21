"""
Settings API: products and users.

  GET    /api/products            any logged-in user (POS will need the menu)
  POST   /api/products            Owner
  PUT    /api/products/<id>       Owner (send only the fields to change)
  DELETE /api/products/<id>       Owner. A product that already has sales or inventory
                                  is hidden (Unavailable) instead of deleted.
  GET    /api/users               Owner
  POST   /api/users               Owner (password is stored hashed)
  PUT    /api/users/<id>          Owner (name / role / active)

Uses the same temporary X-Username login as transactions.py.
"""
import re
from decimal import Decimal

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from transactions import ApiError, audit, current_user, handle_api_error, json_body, num, require_owner, to_money, with_db

bp = Blueprint("settings", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)

CATEGORIES = ("Coffee", "Non-Coffee", "Refreshers")   # same as the product_category enum
ROLES = ("Owner", "Barista")
MAX_MONEY = Decimal("99999999.99")                      # NUMERIC(10,2)


# ---------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------
def clean_text(value, label, max_len=45):
    text = str(value or "").strip()
    if not text:
        raise ApiError(422, f"{label} is required.")
    if len(text) > max_len:
        raise ApiError(422, f"{label} is too long ({max_len} characters max).")
    return text


def clean_money(value, label):
    amount = to_money(value, label)
    if amount < 0:
        raise ApiError(422, f"{label} can't be negative.")
    if amount > MAX_MONEY:
        raise ApiError(422, f"{label} is too large.")
    return amount


def clean_category(value):
    if value not in CATEGORIES:
        raise ApiError(422, "Category must be Coffee, Non-Coffee or Refreshers.")
    return value


# ---------------------------------------------------------------
# Products
# ---------------------------------------------------------------
PRODUCT_SELECT = """
    SELECT productid, productname, category::text AS category, sellingprice,
           productcost, packagingcost, isavailable
    FROM product
"""


def serialize_product(r):
    return {
        "id": r["productid"],
        "name": r["productname"],
        "category": r["category"],
        "price": num(r["sellingprice"]),
        "packagingCost": num(r["packagingcost"]),
        "cost": num(r["productcost"]),
        "available": r["isavailable"],
    }


def get_product(cur, product_id):
    cur.execute(PRODUCT_SELECT + " WHERE productid = %s", (product_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "Product not found.")
    return serialize_product(row)


def check_name_free(cur, name, ignore_id=None):
    cur.execute(
        "SELECT 1 FROM product WHERE lower(productname) = lower(%s) AND productid <> COALESCE(%s, -1)",
        (name, ignore_id),
    )
    if cur.fetchone():
        raise ApiError(409, f"There is already a product named {name}.")


@bp.get("/products")
@with_db
def list_products(cur):
    current_user(cur)
    sql = PRODUCT_SELECT
    if request.args.get("available") == "true":
        sql += " WHERE isavailable"
    cur.execute(sql + " ORDER BY category, productname")
    return jsonify([serialize_product(r) for r in cur.fetchall()])


@bp.post("/products")
@with_db
def add_product(cur):
    user = require_owner(cur)
    body = json_body()
    name = clean_text(body.get("name"), "Product name")
    category = clean_category(body.get("category"))
    price = clean_money(body.get("price"), "Selling price")
    packaging = clean_money(body.get("packagingCost", 0), "Packaging cost")
    available = bool(body.get("available", True))
    check_name_free(cur, name)

    cur.execute(
        """INSERT INTO product (productname, category, sellingprice, packagingcost, isavailable)
           VALUES (%s, %s::product_category, %s, %s, %s) RETURNING productid""",
        (name, category, price, packaging, available),
    )
    product_id = cur.fetchone()["productid"]
    audit(cur, user["userid"], f"Added product {name}", "PRODUCT", product_id)
    return jsonify(get_product(cur, product_id)), 201


@bp.put("/products/<int:product_id>")
@with_db
def update_product(cur, product_id):
    user = require_owner(cur)
    body = json_body()
    current = get_product(cur, product_id)

    name = clean_text(body["name"], "Product name") if "name" in body else current["name"]
    category = clean_category(body["category"]) if "category" in body else current["category"]
    price = clean_money(body["price"], "Selling price") if "price" in body else Decimal(str(current["price"]))
    packaging = clean_money(body["packagingCost"], "Packaging cost") if "packagingCost" in body else Decimal(str(current["packagingCost"]))
    available = bool(body["available"]) if "available" in body else current["available"]
    check_name_free(cur, name, product_id)

    cur.execute(
        """UPDATE product SET productname = %s, category = %s::product_category, sellingprice = %s,
                  packagingcost = %s, isavailable = %s WHERE productid = %s""",
        (name, category, price, packaging, available, product_id),
    )
    audit(cur, user["userid"], f"Updated product {name}", "PRODUCT", product_id)
    return jsonify(get_product(cur, product_id))


@bp.delete("/products/<int:product_id>")
@with_db
def delete_product(cur, product_id):
    user = require_owner(cur)
    product = get_product(cur, product_id)
    cur.execute(
        """SELECT EXISTS (SELECT 1 FROM orderitem WHERE productid = %s)
               OR EXISTS (SELECT 1 FROM inventory WHERE productid = %s) AS used""",
        (product_id, product_id),
    )
    if cur.fetchone()["used"]:
        # past sales and stock point at this product, so keep the row and just hide it
        cur.execute("UPDATE product SET isavailable = FALSE WHERE productid = %s", (product_id,))
        audit(cur, user["userid"], f"Marked product {product['name']} unavailable", "PRODUCT", product_id)
        return jsonify({"deleted": False, "product": get_product(cur, product_id)})
    cur.execute("DELETE FROM product WHERE productid = %s", (product_id,))
    audit(cur, user["userid"], f"Deleted product {product['name']}", "PRODUCT", product_id)
    return jsonify({"deleted": True, "product": None})


# ---------------------------------------------------------------
# Users
# ---------------------------------------------------------------
USER_SELECT = 'SELECT userid, fullname, username, role, isactive FROM "User"'


def serialize_user(r):
    return {"id": r["userid"], "name": r["fullname"], "username": r["username"], "role": r["role"], "active": r["isactive"]}


def get_user(cur, user_id):
    cur.execute(USER_SELECT + " WHERE userid = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "User not found.")
    return serialize_user(row)


@bp.get("/users")
@with_db
def list_users(cur):
    require_owner(cur)
    cur.execute(USER_SELECT + " ORDER BY userid")
    return jsonify([serialize_user(r) for r in cur.fetchall()])


@bp.post("/users")
@with_db
def add_user(cur):
    owner = require_owner(cur)
    body = json_body()
    name = clean_text(body.get("name"), "Full name")
    username = str(body.get("username") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,45}", username):
        raise ApiError(422, "Username must be 3 to 45 letters, numbers, dots, dashes or underscores.")
    role = body.get("role")
    if role not in ROLES:
        raise ApiError(422, "Role must be Owner or Barista.")
    password = str(body.get("password") or "")
    if len(password) < 6:
        raise ApiError(422, "Password must be at least 6 characters.")
    if len(password) > 128:
        raise ApiError(422, "Password is too long.")

    cur.execute('SELECT 1 FROM "User" WHERE lower(username) = lower(%s)', (username,))
    if cur.fetchone():
        raise ApiError(409, f"The username {username} is already taken.")

    cur.execute(
        'INSERT INTO "User" (fullname, username, password, role) VALUES (%s, %s, %s, %s) RETURNING userid',
        (name, username, generate_password_hash(password), role),
    )
    user_id = cur.fetchone()["userid"]
    audit(cur, owner["userid"], f"Added user {username} ({role})", "USER", user_id)
    return jsonify(get_user(cur, user_id)), 201


@bp.put("/users/<int:user_id>")
@with_db
def update_user(cur, user_id):
    owner = require_owner(cur)
    body = json_body()
    target = get_user(cur, user_id)

    name = clean_text(body["name"], "Full name") if "name" in body else target["name"]
    role = body["role"] if "role" in body else target["role"]
    if role not in ROLES:
        raise ApiError(422, "Role must be Owner or Barista.")
    active = bool(body["active"]) if "active" in body else target["active"]

    if user_id == owner["userid"] and not active:
        raise ApiError(409, "You can't deactivate your own account.")
    loses_owner = target["role"] == "Owner" and target["active"] and (role != "Owner" or not active)
    if loses_owner:
        cur.execute(
            """SELECT COUNT(*) AS n FROM "User" WHERE role = 'Owner' AND isactive AND userid <> %s""",
            (user_id,),
        )
        if cur.fetchone()["n"] == 0:
            raise ApiError(409, "There must be at least one active Owner.")

    cur.execute(
        'UPDATE "User" SET fullname = %s, role = %s, isactive = %s WHERE userid = %s',
        (name, role, active, user_id),
    )
    what = "Activated" if active and not target["active"] else "Deactivated" if target["active"] and not active else "Updated"
    audit(cur, owner["userid"], f"{what} user {target['username']}", "USER", user_id)
    return jsonify(get_user(cur, user_id))
