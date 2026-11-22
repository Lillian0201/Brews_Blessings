"""
Brews & Blessings - command-line API tests.

Run it in the VS Code terminal while the backend is running:

    cd backend
    python api_tests.py

It needs no extra install (standard library only). Each test prints PASS or
FAIL as it runs, then a summary, and saves a report you can use as your
test documentation:

    test_results_<date>_<time>.csv   (open in Excel)
    test_results_<date>_<time>.md    (readable table)

Everything it creates is named "AUTOTEST ..." so it is easy to find and to
remove with cleanup_test_data.sql afterwards.

Options:
    python api_tests.py --url http://127.0.0.1:5001/api    (different server)
    python api_tests.py --no-color                         (plain text)
    python api_tests.py --only SET                         (only IDs containing SET)

It uses the seeded 'owner' and 'barista' usernames through the X-Username
header, like the frontend does. One test (TC-POS-13) also adds a temporary
recipe straight into the database using backend/.env, so run it from the
backend folder with the same Python environment as the backend.
"""
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------
# Settings
# ---------------------------------------------------------------
BASE = os.environ.get("BB_API", "http://127.0.0.1:5001/api")
USE_COLOR = "--no-color" not in sys.argv
OWNER, BARISTA = "owner", "barista"
STAMP = datetime.datetime.now().strftime("%y%m%d%H%M%S")

if "--url" in sys.argv:
    BASE = sys.argv[sys.argv.index("--url") + 1].rstrip("/")
ONLY = sys.argv[sys.argv.index("--only") + 1].upper() if "--only" in sys.argv else None

if os.name == "nt":
    os.system("")  # lets the Windows terminal show colors


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


GREEN, RED, YELLOW, CYAN, DIM = "32", "31", "33", "36", "2"


# ---------------------------------------------------------------
# Small HTTP helper
# ---------------------------------------------------------------
def call(method, path, body=None, user=OWNER):
    headers = {}
    if user:
        headers["X-Username"] = user
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    try:
        payload = json.loads(raw) if raw else None
    except ValueError:
        payload = None
    return status, payload


def detail(payload):
    if isinstance(payload, dict) and payload.get("detail"):
        return payload["detail"]
    return ""


class Skip(Exception):
    pass


def expect(res, *codes):
    """Check the HTTP status. res is the (status, payload) from call()."""
    status, payload = res
    if status not in codes:
        want = " or ".join(str(c) for c in codes)
        raise AssertionError(f"expected status {want}, got {status} {detail(payload)}".strip())
    return payload


def expect_4xx(res):
    status, payload = res
    if not 400 <= status < 500:
        raise AssertionError(f"expected a 4xx error, got {status} {detail(payload)}".strip())
    return payload


def need(key):
    if key not in S:
        raise Skip(f"needs '{key}' from an earlier test")
    return S[key]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


# ---------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------
TESTS = []   # (id, module, title, expected, function)
S = {}       # shared state between tests


def test(tid, module, title, expected):
    def wrap(fn):
        TESTS.append((tid, module, title, expected, fn))
        return fn
    return wrap


# ================================================================
# 1. Server and login
# ================================================================
@test("TC-API-01", "Server", "Health check", "GET /api/health returns 200 and status ok")
def _():
    body = expect(call("GET", "/health", user=None), 200)
    check(body and body.get("status") == "ok", f"unexpected body {body}")
    return "200 status ok"


@test("TC-AUTH-01", "Login", "Request without a username is refused",
      "GET /api/expenses with no X-Username returns 401")
def _():
    expect(call("GET", "/expenses", user=None), 401)
    return "401 Not logged in"


@test("TC-AUTH-02", "Login", "Unknown username is refused",
      "GET /api/expenses as 'nobody_here' returns 401")
def _():
    expect(call("GET", "/expenses", user="nobody_here"), 401)
    return "401 Unknown user"


@test("TC-AUTH-03", "Login", "Barista cannot open Owner-only data",
      "GET /api/expenses as barista returns 403")
def _():
    expect(call("GET", "/expenses", user=BARISTA), 403)
    return "403 Only the Owner can do this"


@test("TC-AUTH-04", "Login", "Login with empty fields",
      "POST /api/login with empty username and password returns 422")
def _():
    expect(call("POST", "/login", {"username": "", "password": ""}, user=None), 422)
    return "422 Enter your username and password"


@test("TC-AUTH-05", "Login", "Login with an unknown account",
      "POST /api/login with a wrong user returns 401 Invalid username or password")
def _():
    expect(call("POST", "/login", {"username": "nobody_here", "password": "whatever1"}, user=None), 401)
    return "401 Invalid username or password"


# ================================================================
# 2. Settings - Users
# ================================================================
S["username"] = f"autotest{STAMP}"
S["password"] = "test1234"


@test("TC-USR-01", "Settings - Users", "Add a user",
      "POST /api/users creates a Barista and returns 201 without the password")
def _():
    body = expect(call("POST", "/users", {
        "name": f"AUTOTEST Barista {STAMP}", "username": S["username"],
        "role": "Barista", "password": S["password"]}), 201)
    check(body.get("username") == S["username"], "username missing in response")
    check("password" not in json.dumps(body).lower(), "response must not contain the password")
    S["user_id"] = body["id"]
    return f"201 created user id {body['id']}"


@test("TC-USR-02", "Settings - Users", "Duplicate username is refused",
      "Adding the same username again returns 409")
def _():
    need("user_id")
    expect(call("POST", "/users", {"name": "AUTOTEST Dup", "username": S["username"],
                                   "role": "Barista", "password": S["password"]}), 409)
    return "409 username already taken"


@test("TC-USR-03", "Settings - Users", "Short password is refused",
      "Adding a user with a 3-character password returns 422")
def _():
    expect(call("POST", "/users", {"name": "AUTOTEST Short", "username": f"autotestshort{STAMP}",
                                   "role": "Barista", "password": "abc"}), 422)
    return "422 password too short"


@test("TC-USR-04", "Settings - Users", "Invalid role is refused",
      "Adding a user with role 'Manager' returns 422")
def _():
    expect(call("POST", "/users", {"name": "AUTOTEST Role", "username": f"autotestrole{STAMP}",
                                   "role": "Manager", "password": "test1234"}), 422)
    return "422 role must be Owner or Barista"


@test("TC-USR-05", "Settings - Users", "Owner can list users",
      "GET /api/users as owner returns 200 and includes the new user")
def _():
    need("user_id")
    users = expect(call("GET", "/users"), 200)
    check(any(u.get("username") == S["username"] for u in users), "new user not in the list")
    return f"200, {len(users)} users listed"


@test("TC-USR-06", "Settings - Users", "Barista cannot list users",
      "GET /api/users as barista returns 403")
def _():
    expect(call("GET", "/users", user=BARISTA), 403)
    return "403 Owner only"


@test("TC-AUTH-06", "Login", "Login with the new user's password",
      "POST /api/login with the correct password returns 200 and role Barista")
def _():
    need("user_id")
    body = expect(call("POST", "/login", {"username": S["username"], "password": S["password"]}, user=None), 200)
    check(body.get("role") == "Barista", f"role was {body.get('role')}")
    return "200 role Barista"


@test("TC-AUTH-07", "Login", "Login is not case sensitive for the username",
      "Logging in with the username in capitals still returns 200")
def _():
    need("user_id")
    expect(call("POST", "/login", {"username": S["username"].upper(), "password": S["password"]}, user=None), 200)
    return "200"


@test("TC-AUTH-08", "Login", "Wrong password is refused",
      "POST /api/login with a wrong password returns 401")
def _():
    need("user_id")
    expect(call("POST", "/login", {"username": S["username"], "password": "wrong-pass"}, user=None), 401)
    return "401 Invalid username or password"


@test("TC-USR-07", "Settings - Users", "Deactivate a user",
      "PUT /api/users/<id> with active=false returns 200 and active false")
def _():
    uid = need("user_id")
    body = expect(call("PUT", f"/users/{uid}", {"active": False}), 200)
    check(body.get("active") is False, f"active was {body.get('active')}")
    return "200 active=false"


@test("TC-AUTH-09", "Login", "Deactivated user cannot log in",
      "POST /api/login for an inactive user returns 401")
def _():
    need("user_id")
    expect(call("POST", "/login", {"username": S["username"], "password": S["password"]}, user=None), 401)
    return "401 inactive account refused"


@test("TC-USR-08", "Settings - Users", "Reactivate a user",
      "PUT /api/users/<id> with active=true returns 200 and active true")
def _():
    uid = need("user_id")
    body = expect(call("PUT", f"/users/{uid}", {"active": True}), 200)
    check(body.get("active") is True, f"active was {body.get('active')}")
    return "200 active=true"


@test("TC-USR-09", "Settings - Users", "Owner cannot deactivate themself",
      "Owner deactivating their own account returns 409")
def _():
    users = expect(call("GET", "/users"), 200)
    me = next((u for u in users if u.get("username", "").lower() == OWNER), None)
    check(me is not None, "owner account not found")
    expect(call("PUT", f"/users/{me['id']}", {"active": False}), 409)
    return "409 can't deactivate your own account"


# ================================================================
# 3. Settings - Products
# ================================================================
S["product_name"] = f"AUTOTEST Latte {STAMP}"


@test("TC-PRD-01", "Settings - Products", "Add a product",
      "POST /api/products returns 201 with the saved name, category and price")
def _():
    body = expect(call("POST", "/products", {
        "name": S["product_name"], "category": "Coffee", "price": 100,
        "packagingCost": 8, "available": True}), 201)
    check(body.get("name") == S["product_name"], "name not saved")
    check(float(body.get("price")) == 100.0, f"price was {body.get('price')}")
    S["product_id"] = body["id"]
    return f"201 created product id {body['id']}"


@test("TC-PRD-02", "Settings - Products", "Duplicate product name is refused",
      "Adding the same product name again returns 409")
def _():
    need("product_id")
    expect(call("POST", "/products", {"name": S["product_name"], "category": "Coffee", "price": 100}), 409)
    return "409 name already exists"


@test("TC-PRD-03", "Settings - Products", "Invalid category is refused",
      "Adding a product with category 'Pastry' returns 422")
def _():
    expect(call("POST", "/products", {"name": f"AUTOTEST Bad {STAMP}", "category": "Pastry", "price": 50}), 422)
    return "422 category must be Coffee, Non-Coffee or Refreshers"


@test("TC-PRD-04", "Settings - Products", "Negative price is refused",
      "Adding a product with price -5 returns 422")
def _():
    expect(call("POST", "/products", {"name": f"AUTOTEST Neg {STAMP}", "category": "Coffee", "price": -5}), 422)
    return "422 invalid price"


@test("TC-PRD-05", "Settings - Products", "Empty product name is refused",
      "Adding a product with a blank name returns 422")
def _():
    expect(call("POST", "/products", {"name": "   ", "category": "Coffee", "price": 50}), 422)
    return "422 name required"


@test("TC-PRD-06", "Settings - Products", "Product appears in the list",
      "GET /api/products includes the new product")
def _():
    need("product_id")
    items = expect(call("GET", "/products"), 200)
    check(any(p.get("name") == S["product_name"] for p in items), "new product not in the list")
    return f"200, {len(items)} products listed"


@test("TC-PRD-07", "Settings - Products", "Edit a product price",
      "PUT /api/products/<id> with price 120 returns 200 and the new price")
def _():
    pid = need("product_id")
    body = expect(call("PUT", f"/products/{pid}", {"price": 120}), 200)
    check(float(body.get("price")) == 120.0, f"price was {body.get('price')}")
    return "200 price 120"


@test("TC-PRD-08", "Settings - Products", "Hide a product from the menu",
      "PUT with available=false makes it disappear from /api/products?available=true")
def _():
    pid = need("product_id")
    expect(call("PUT", f"/products/{pid}", {"available": False}), 200)
    items = expect(call("GET", "/products?available=true"), 200)
    check(not any(p.get("id") == pid for p in items), "unavailable product still listed")
    expect(call("PUT", f"/products/{pid}", {"available": True}), 200)
    return "200 hidden, then restored"


@test("TC-PRD-09", "Settings - Products", "Barista cannot add products",
      "POST /api/products as barista returns 403")
def _():
    expect(call("POST", "/products", {"name": f"AUTOTEST Barista {STAMP}", "category": "Coffee",
                                      "price": 10}, user=BARISTA), 403)
    return "403 Owner only"


@test("TC-PRD-10", "Settings - Products", "Delete a product that was never sold",
      "DELETE removes it completely (deleted true)")
def _():
    body = expect(call("POST", "/products", {"name": f"AUTOTEST Delete {STAMP}",
                                             "category": "Refreshers", "price": 69}), 201)
    res = expect(call("DELETE", f"/products/{body['id']}"), 200)
    check(res.get("deleted") is True, f"deleted was {res.get('deleted')}")
    items = expect(call("GET", "/products"), 200)
    check(not any(p.get("id") == body["id"] for p in items), "product still listed after delete")
    return "200 deleted true"


# ================================================================
# 4. Expense
# ================================================================
@test("TC-EXP-01", "Expense", "Add an expense",
      "POST /api/expenses returns 201 with the type, amount and description")
def _():
    body = expect(call("POST", "/expenses", {"type": "Electricity", "amount": "2500.50",
                                             "description": f"AUTOTEST electric bill {STAMP}"}), 201)
    check(float(body.get("amount")) == 2500.50, f"amount was {body.get('amount')}")
    S["expense_id"] = body.get("id")
    return "201 saved"


@test("TC-EXP-02", "Expense", "Expense appears in the list after saving",
      "GET /api/expenses includes the new expense (so it is stored in the database)")
def _():
    need("expense_id")
    items = expect(call("GET", "/expenses"), 200)
    check(any(f"AUTOTEST electric bill {STAMP}" in str(e.get("description")) for e in items),
          "expense not found in the list")
    return f"200, {len(items)} expenses listed"


@test("TC-EXP-03", "Expense", "Filter expenses by type",
      "GET /api/expenses?type=Electricity returns only Electricity rows")
def _():
    items = expect(call("GET", "/expenses?type=Electricity"), 200)
    check(items and all(e.get("type") == "Electricity" for e in items), "other types came back")
    return f"200, {len(items)} Electricity rows"


@test("TC-EXP-04", "Expense", "Filter expenses by date",
      "GET /api/expenses with today's date range includes the new expense")
def _():
    need("expense_id")
    today = datetime.date.today().isoformat()
    items = expect(call("GET", f"/expenses?date_from={today}&date_to={today}"), 200)
    check(any(f"AUTOTEST electric bill {STAMP}" in str(e.get("description")) for e in items),
          "today's expense missing")
    return "200"


@test("TC-EXP-05", "Expense", "Zero amount is refused",
      "Saving an expense of 0 returns 422")
def _():
    expect(call("POST", "/expenses", {"type": "Supplies", "amount": 0, "description": "AUTOTEST zero"}), 422)
    return "422 amount must be more than zero"


@test("TC-EXP-06", "Expense", "Negative amount is refused",
      "Saving an expense of -50 returns 422")
def _():
    expect(call("POST", "/expenses", {"type": "Supplies", "amount": -50, "description": "AUTOTEST negative"}), 422)
    return "422"


@test("TC-EXP-07", "Expense", "Empty description is refused",
      "Saving an expense with a blank description returns 422")
def _():
    expect(call("POST", "/expenses", {"type": "Supplies", "amount": 10, "description": "  "}), 422)
    return "422 description required"


@test("TC-EXP-08", "Expense", "Invalid type is refused",
      "Saving an expense with type 'Gifts' returns 422")
def _():
    expect(call("POST", "/expenses", {"type": "Gifts", "amount": 10, "description": "AUTOTEST type"}), 422)
    return "422 invalid type"


@test("TC-EXP-09", "Expense", "Bad date is refused",
      "Saving an expense with date 'tomorrow' returns 422")
def _():
    expect(call("POST", "/expenses", {"type": "Supplies", "amount": 10, "description": "AUTOTEST date",
                                      "date": "tomorrow"}), 422)
    return "422 date format"


@test("TC-EXP-10", "Expense", "Barista cannot add expenses",
      "POST /api/expenses as barista returns 403")
def _():
    expect(call("POST", "/expenses", {"type": "Supplies", "amount": 10, "description": "AUTOTEST barista"},
                user=BARISTA), 403)
    return "403 Owner only"


# ================================================================
# 5. Inventory
# ================================================================
S["ingredient"] = f"AUTOTEST Beans {STAMP}"


def stock_of(ingredient_id):
    items = expect(call("GET", "/inventory"), 200)
    row = next((i for i in items if i.get("id") == ingredient_id), None)
    check(row is not None, "ingredient not in the inventory list")
    return float(row["remaining"]), row


@test("TC-INV-01", "Inventory", "Add an inventory item",
      "POST /api/inventory/items returns 201 with an id")
def _():
    body = expect(call("POST", "/inventory/items", {"name": S["ingredient"], "unit": "g",
                                                    "unitCost": 1.2, "reorderLevel": 5}), 201)
    S["ingredient_id"] = body["id"]
    return f"201 created ingredient id {body['id']}"


@test("TC-INV-02", "Inventory", "Duplicate item is refused",
      "Adding the same item name again returns 409")
def _():
    need("ingredient_id")
    expect(call("POST", "/inventory/items", {"name": S["ingredient"], "unit": "g"}), 409)
    return "409 item already exists"


@test("TC-INV-03", "Inventory", "Item needs a name and unit",
      "Adding an item with no unit returns 422")
def _():
    expect(call("POST", "/inventory/items", {"name": f"AUTOTEST NoUnit {STAMP}", "unit": ""}), 422)
    return "422"


@test("TC-INV-04", "Inventory", "Barista cannot add inventory items",
      "POST /api/inventory/items as barista returns 403")
def _():
    expect(call("POST", "/inventory/items", {"name": f"AUTOTEST B {STAMP}", "unit": "g"}, user=BARISTA), 403)
    return "403 Owner only"


@test("TC-INV-05", "Inventory", "Stock in",
      "Stock-in of 10 with a batch number returns 200 and remaining becomes 10")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-in", {"ingredientId": iid, "quantity": 10,
                                                "batchNo": f"AUTOTEST-{STAMP}"}), 200)
    remaining, row = stock_of(iid)
    check(remaining == 10.0, f"remaining was {remaining}")
    return "200 remaining 10"


@test("TC-INV-06", "Inventory", "Stock in needs a batch number",
      "Stock-in with no batch number returns 422")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-in", {"ingredientId": iid, "quantity": 5}), 422)
    return "422 enter a batch number"


@test("TC-INV-07", "Inventory", "Stock in rejects zero or negative quantity",
      "Stock-in with quantity 0 returns 422")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-in", {"ingredientId": iid, "quantity": 0, "batchNo": "AUTOTEST-X"}), 422)
    return "422 quantity must be more than zero"


@test("TC-INV-08", "Inventory", "Stock out",
      "Stock-out of 3 returns 200 and remaining becomes 7")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-out", {"ingredientId": iid, "quantity": 3}), 200)
    remaining, _row = stock_of(iid)
    check(remaining == 7.0, f"remaining was {remaining}")
    return "200 remaining 7"


@test("TC-INV-09", "Inventory", "Cannot stock out more than is left",
      "Stock-out of 999 is refused with a 4xx error and stock stays at 7")
def _():
    iid = need("ingredient_id")
    expect_4xx(call("POST", "/inventory/stock-out", {"ingredientId": iid, "quantity": 999}))
    remaining, _row = stock_of(iid)
    check(remaining == 7.0, f"remaining changed to {remaining}")
    return "4xx refused, stock still 7"


@test("TC-INV-10", "Inventory", "Waste needs a reason",
      "Waste without a reason returns 422")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-out", {"ingredientId": iid, "quantity": 1, "type": "Waste"}), 422)
    return "422 enter a reason"


@test("TC-INV-11", "Inventory", "Record waste with a reason",
      "Waste of 1 with a reason returns 200 and remaining becomes 6")
def _():
    iid = need("ingredient_id")
    expect(call("POST", "/inventory/stock-out", {"ingredientId": iid, "quantity": 1, "type": "Waste",
                                                 "reason": "AUTOTEST spilled"}), 200)
    remaining, _row = stock_of(iid)
    check(remaining == 6.0, f"remaining was {remaining}")
    return "200 remaining 6"


@test("TC-INV-12", "Inventory", "Status changes at the reorder level",
      "With 6 left and reorder level 5 the status is Available; after using 2 more it is Low-Stock")
def _():
    iid = need("ingredient_id")
    _rem, row = stock_of(iid)
    check(row["status"] == "Available", f"status was {row['status']}")
    expect(call("POST", "/inventory/stock-out", {"ingredientId": iid, "quantity": 2}), 200)
    _rem, row = stock_of(iid)
    check(row["status"] == "Low-Stock", f"status was {row['status']}")
    return "Available -> Low-Stock"


@test("TC-INV-13", "Inventory", "Movement history is recorded",
      "GET /api/inventory/movements shows Stock-In, Stock-Out and Waste for the item")
def _():
    need("ingredient_id")
    rows = expect(call("GET", "/inventory/movements"), 200)
    types = {m["type"] for m in rows if m.get("item") == S["ingredient"]}
    check({"Stock-In", "Stock-Out", "Waste"} <= types, f"found only {sorted(types)}")
    return f"found {sorted(types)}"


# ================================================================
# 6. POS orders
# ================================================================
def make_order(qty=2, price=100, tendered=200, discount=0, payment="Cash"):
    pid = need("product_id")
    return call("POST", "/orders", {
        "items": [{"productId": pid, "qty": qty, "price": price}],
        "discountPercent": discount, "payment": payment, "tendered": tendered,
        "customer": f"AUTOTEST Customer {STAMP}"})


@test("TC-POS-01", "POS", "Create a cash order",
      "2 x 100 paid with 250 returns 201, total 200 and change 50")
def _():
    body = expect(make_order(qty=2, price=100, tendered=250), 201)
    check(float(body["total"]) == 200.0, f"total was {body['total']}")
    check(float(body["change"]) == 50.0, f"change was {body['change']}")
    S["order_cancel"] = body
    return f"201 order {body['orderNumber']}, total 200, change 50"


@test("TC-POS-02", "POS", "Discount is applied",
      "1 x 100 with 10% discount paid with 100 gives total 90 and change 10")
def _():
    body = expect(make_order(qty=1, price=100, tendered=100, discount=10), 201)
    check(float(body["total"]) == 90.0, f"total was {body['total']}")
    check(float(body["change"]) == 10.0, f"change was {body['change']}")
    return "201 total 90, change 10"


@test("TC-POS-03", "POS", "Cash that is too small is refused",
      "Tendered 50 for a 200 order returns 422 and says it is short")
def _():
    need("product_id")
    res = make_order(qty=2, price=100, tendered=50)
    expect(res, 422)
    check("short" in detail(res[1]).lower(), f"message was '{detail(res[1])}'")
    return "422 amount tendered is short"


@test("TC-POS-04", "POS", "Empty order is refused",
      "Creating an order with no items returns 422")
def _():
    expect(call("POST", "/orders", {"items": [], "payment": "Cash", "tendered": 0}), 422)
    return "422 add at least one item"


@test("TC-POS-05", "POS", "Quantity above 99 is refused",
      "Creating an order with quantity 100 returns 422")
def _():
    need("product_id")
    expect(make_order(qty=100, price=100, tendered=999999), 422)
    return "422 quantity must be between 1 and 99"


@test("TC-POS-06", "POS", "Unavailable product cannot be ordered",
      "Ordering a hidden product returns 422")
def _():
    pid = need("product_id")
    expect(call("PUT", f"/products/{pid}", {"available": False}), 200)
    try:
        expect(make_order(qty=1, price=100, tendered=100), 422)
    finally:
        call("PUT", f"/products/{pid}", {"available": True})
    return "422 product is not available"


@test("TC-POS-07", "POS", "Order can be read back",
      "GET /api/orders/<id> returns the order with its items")
def _():
    order = need("order_cancel")
    body = expect(call("GET", f"/orders/{order['id']}"), 200)
    check(body.get("items") and body["items"][0]["qty"] == 2, "items not saved correctly")
    return "200 items match"


@test("TC-POS-08", "POS", "Order appears in the orders list",
      "GET /api/orders includes the new order number")
def _():
    order = need("order_cancel")
    rows = expect(call("GET", "/orders"), 200)
    check(order["orderNumber"] in json.dumps(rows), "order number not found in the list")
    return f"200, {len(rows)} orders listed"


@test("TC-POS-09", "POS", "Cancelling needs a reason",
      "PATCH status Cancelled with no reason returns 422")
def _():
    order = need("order_cancel")
    expect(call("PATCH", f"/orders/{order['id']}/status", {"status": "Cancelled"}), 422)
    return "422 enter a reason"


@test("TC-POS-10", "POS", "Cancel an order",
      "PATCH status Cancelled with a reason returns 200 and the order shows Cancelled")
def _():
    order = need("order_cancel")
    expect(call("PATCH", f"/orders/{order['id']}/status", {"status": "Cancelled", "reason": "AUTOTEST cancel"}), 200)
    body = expect(call("GET", f"/orders/{order['id']}"), 200)
    check(body.get("status") == "Cancelled" or body.get("orderStatus") == "Cancelled"
          or "Cancelled" in json.dumps(body), "status did not change to Cancelled")
    return "200 Cancelled"


@test("TC-POS-11", "POS", "Invalid status is refused",
      "PATCH status 'Shipped' returns 422")
def _():
    order = need("order_cancel")
    expect(call("PATCH", f"/orders/{order['id']}/status", {"status": "Shipped"}), 422)
    return "422"


@test("TC-POS-12", "POS", "Unknown order returns 404",
      "GET /api/orders/99999999 returns 404")
def _():
    expect(call("GET", "/orders/99999999"), 404)
    return "404 Order not found"


@test("TC-POS-13", "POS", "Stock is used by an order and restored by a cancel",
      "With a recipe of 1 unit per drink, an order of 2 takes 2 from stock, a cancel puts them back, and re-completing takes them again")
def _():
    pid = need("product_id")
    try:
        from db import get_conn   # uses the same .env as the backend
        conn = get_conn()
    except Exception as why:
        raise Skip(f"could not connect to the database for the recipe: {why}")

    # a separate AUTOTEST ingredient with 10 in stock
    name = f"AUTOTEST Recipe Item {STAMP}"
    body = expect(call("POST", "/inventory/items", {"name": name, "unit": "pc", "reorderLevel": 1}), 201)
    iid = body["id"]
    expect(call("POST", "/inventory/stock-in", {"ingredientId": iid, "quantity": 10,
                                                "batchNo": f"AUTOTEST-R{STAMP}"}), 200)
    check(stock_of(iid)[0] == 10.0, "starting stock is not 10")

    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO recipe (productid, ingredientid, qtyused) VALUES (%s, %s, 1) "
                    "ON CONFLICT DO NOTHING", (pid, iid))
        conn.commit()

        order = expect(make_order(qty=2, price=100, tendered=200), 201)
        check(stock_of(iid)[0] == 8.0, f"after the order stock was {stock_of(iid)[0]}, expected 8")

        expect(call("PATCH", f"/orders/{order['id']}/status",
                    {"status": "Cancelled", "reason": "AUTOTEST restore stock"}), 200)
        check(stock_of(iid)[0] == 10.0, f"after the cancel stock was {stock_of(iid)[0]}, expected 10")

        expect(call("PATCH", f"/orders/{order['id']}/status", {"status": "Completed"}), 200)
        check(stock_of(iid)[0] == 8.0, f"after re-completing stock was {stock_of(iid)[0]}, expected 8")
    finally:
        # remove the recipe so later tests that use this product do not touch stock
        cur.execute("DELETE FROM recipe WHERE productid = %s AND ingredientid = %s", (pid, iid))
        conn.commit()
        conn.close()
    return "stock 10 -> 8 (order) -> 10 (cancel) -> 8 (re-complete)"


# ================================================================
# 7. Transactions - void and refund
# ================================================================
def new_sale(key, qty=1, price=100):
    body = expect(make_order(qty=qty, price=price, tendered=qty * price), 201)
    S[key] = body
    return body


@test("TC-TRX-01", "Transactions", "Sales list loads",
      "GET /api/transactions?tab=sales returns 200 with a list")
def _():
    rows = expect(call("GET", "/transactions?tab=sales"), 200)
    check(isinstance(rows, list), "not a list")
    return f"200, {len(rows)} rows"


@test("TC-TRX-02", "Transactions", "All four tabs load",
      "The sales, discounts, voided and refunded tabs each return 200")
def _():
    for tab in ("sales", "discounts", "voided", "refunded"):
        expect(call("GET", f"/transactions?tab={tab}"), 200)
    return "200 on all four tabs"


@test("TC-TRX-03", "Transactions", "A new sale shows in the sales list",
      "A completed order appears in /api/transactions and can be found by its number")
def _():
    sale = new_sale("sale_void")
    rows = expect(call("GET", f"/transactions?tab=sales&q={sale['orderNumber']}"), 200)
    check(sale["orderNumber"] in json.dumps(rows), "sale not found by order number")
    return f"200 found order {sale['orderNumber']}"


@test("TC-TRX-04", "Transactions", "Payment filter works",
      "GET /api/transactions?payment=Cash returns 200")
def _():
    expect(call("GET", "/transactions?tab=sales&payment=Cash"), 200)
    return "200"


@test("TC-TRX-05", "Transactions", "Void needs a reason",
      "Voiding without a reason returns 422")
def _():
    sale = need("sale_void")
    expect(call("POST", f"/transactions/{sale['id']}/void", {"reason": ""}), 422)
    return "422 reason required"


@test("TC-TRX-06", "Transactions", "Barista cannot void a sale",
      "Voiding as barista returns 403")
def _():
    sale = need("sale_void")
    expect(call("POST", f"/transactions/{sale['id']}/void", {"reason": "AUTOTEST"}, user=BARISTA), 403)
    return "403 Owner only"


@test("TC-TRX-07", "Transactions", "Void a sale",
      "Voiding with a reason returns 200 and the sale appears in the voided tab")
def _():
    sale = need("sale_void")
    expect(call("POST", f"/transactions/{sale['id']}/void", {"reason": "AUTOTEST void"}), 200)
    rows = expect(call("GET", f"/transactions?tab=voided&q={sale['orderNumber']}"), 200)
    check(sale["orderNumber"] in json.dumps(rows), "voided sale not in the voided tab")
    return "200 voided"


@test("TC-TRX-08", "Transactions", "A voided sale cannot be voided again",
      "Voiding the same sale again returns 409")
def _():
    sale = need("sale_void")
    expect(call("POST", f"/transactions/{sale['id']}/void", {"reason": "AUTOTEST again"}), 409)
    return "409 only Completed sales can be voided"


def pending_refund_id(order_id):
    rows = expect(call("GET", "/refunds?status=Pending"), 200)
    row = next((r for r in rows if r.get("saleId") == order_id), None)
    check(row is not None, "pending refund not found in /api/refunds")
    return row["id"]


@test("TC-TRX-09", "Transactions", "Request a refund",
      "Barista requests a refund of 50 for 'Whole order' and gets 201 with status Pending")
def _():
    sale = new_sale("sale_refund")
    expect(call("POST", f"/transactions/{sale['id']}/refunds", {
        "item": "Whole order", "amount": 50, "reason": "AUTOTEST wrong drink"}, user=BARISTA), 201)
    S["refund_id"] = pending_refund_id(sale["id"])
    return f"201 pending refund id {S['refund_id']}"


@test("TC-TRX-10", "Transactions", "Refund larger than the sale is refused",
      "Refund of 5000 on a 100 sale returns 422")
def _():
    sale = new_sale("sale_refund_big")
    expect(call("POST", f"/transactions/{sale['id']}/refunds", {
        "item": "Whole order", "amount": 5000, "reason": "AUTOTEST too big"}), 422)
    return "422 refund can't be more than the sale total"


@test("TC-TRX-11", "Transactions", "Refund needs a reason",
      "A refund request with no reason returns 422")
def _():
    sale = need("sale_refund_big")
    expect(call("POST", f"/transactions/{sale['id']}/refunds", {
        "item": "Whole order", "amount": 10, "reason": ""}), 422)
    return "422 reason required"


@test("TC-TRX-12", "Transactions", "Only one pending refund per sale",
      "A second refund request on the same sale returns 409")
def _():
    sale = need("sale_refund")
    expect(call("POST", f"/transactions/{sale['id']}/refunds", {
        "item": "Whole order", "amount": 10, "reason": "AUTOTEST second"}), 409)
    return "409 already has a pending refund"


@test("TC-TRX-13", "Transactions", "Barista cannot approve a refund",
      "Approving as barista returns 403")
def _():
    rid = need("refund_id")
    expect(call("POST", f"/refunds/{rid}/approve", {}, user=BARISTA), 403)
    return "403 Owner only"


@test("TC-TRX-14", "Transactions", "Owner approves a refund",
      "Approving as owner returns 200 and the refund is no longer Pending")
def _():
    rid = need("refund_id")
    expect(call("POST", f"/refunds/{rid}/approve", {}), 200)
    approved = expect(call("GET", "/refunds?status=Approved"), 200)
    check(any(r.get("id") == rid for r in approved), "refund not in the Approved list")
    return "200 approved"


@test("TC-TRX-15", "Transactions", "An approved refund cannot be approved again",
      "Approving it a second time returns 409")
def _():
    rid = need("refund_id")
    expect(call("POST", f"/refunds/{rid}/approve", {}), 409)
    return "409 already Approved"


@test("TC-TRX-16", "Transactions", "Owner rejects a refund",
      "Rejecting a pending refund returns 200 and it shows as Rejected")
def _():
    sale = new_sale("sale_reject")
    expect(call("POST", f"/transactions/{sale['id']}/refunds", {
        "item": "Whole order", "amount": 20, "reason": "AUTOTEST reject me"}), 201)
    rid = pending_refund_id(sale["id"])
    expect(call("POST", f"/refunds/{rid}/reject", {}), 200)
    rejected = expect(call("GET", "/refunds?status=Rejected"), 200)
    check(any(r.get("id") == rid for r in rejected), "refund not in the Rejected list")
    return "200 rejected"


@test("TC-TRX-17", "Transactions", "Invalid refund status filter is refused",
      "GET /api/refunds?status=Maybe returns 422")
def _():
    expect(call("GET", "/refunds?status=Maybe"), 422)
    return "422"


# ================================================================
# 8. Dashboard
# ================================================================
@test("TC-DSH-01", "Dashboard", "Summary loads",
      "GET /api/dashboard/summary returns 200 with a JSON object")
def _():
    body = expect(call("GET", "/dashboard/summary"), 200)
    check(isinstance(body, dict) and body, "empty or invalid summary")
    return f"200 keys: {', '.join(list(body)[:6])}"


@test("TC-DSH-02", "Dashboard", "Summary needs a login",
      "GET /api/dashboard/summary with no username returns 401")
def _():
    expect(call("GET", "/dashboard/summary", user=None), 401)
    return "401"


# ---------------------------------------------------------------
# Cleanup that can be done through the API
# ---------------------------------------------------------------
def cleanup():
    done = []
    if S.get("user_id"):
        call("PUT", f"/users/{S['user_id']}", {"active": False})
        done.append("test user deactivated")
    if S.get("product_id"):
        res = call("DELETE", f"/products/{S['product_id']}")
        done.append("test product removed or hidden" if res[0] == 200 else "test product not removed")
    return done


# ---------------------------------------------------------------
# Runner
# ---------------------------------------------------------------
def main():
    try:
        call("GET", "/health", user=None)
    except Exception as err:
        print(paint("Cannot reach the backend at " + BASE, RED))
        print("Start it first in another terminal:  cd backend ; python app.py")
        print(f"({err})")
        sys.exit(2)

    selected = [t for t in TESTS if not ONLY or ONLY in t[0] or ONLY in t[1].upper()]
    total = len(selected)
    print(paint(f"\nBrews & Blessings API tests - {BASE}", CYAN))
    print(paint(f"{total} tests, test data is named AUTOTEST {STAMP}\n", DIM))

    results = []
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    module = None
    for n, (tid, mod, title, expected, fn) in enumerate(selected, 1):
        if mod != module:
            module = mod
            print(paint(f"-- {mod} " + "-" * max(4, 60 - len(mod)), CYAN))
        started = time.time()
        try:
            actual = fn() or ""
            status = "PASS"
        except Skip as why:
            status, actual = "SKIP", str(why)
        except AssertionError as why:
            status, actual = "FAIL", str(why)
        except Exception as why:  # network problem, bad JSON, bug in the test
            status, actual = "FAIL", f"{type(why).__name__}: {why}"
        ms = int((time.time() - started) * 1000)
        counts[status] += 1
        color = {"PASS": GREEN, "FAIL": RED, "SKIP": YELLOW}[status]
        print(f"[{n:>2}/{total}] {paint(status, color)}  {tid:<10} {title}  {paint(f'({ms} ms)', DIM)}")
        if status != "PASS":
            print(paint(f"          -> {actual}", color))
        results.append({"id": tid, "module": mod, "test": title, "expected": expected,
                        "actual": actual, "status": status, "ms": ms})

    notes = cleanup()

    print()
    print(paint("=" * 64, CYAN))
    print(f"PASSED {paint(counts['PASS'], GREEN)}   "
          f"FAILED {paint(counts['FAIL'], RED)}   SKIPPED {paint(counts['SKIP'], YELLOW)}   TOTAL {total}")
    for note in notes:
        print(paint(f"cleanup: {note}", DIM))
    print(paint("Remove the leftover AUTOTEST rows with cleanup_test_data.sql in pgAdmin.", DIM))

    ran = datetime.datetime.now()
    name = f"test_results_{ran:%Y%m%d_%H%M%S}"
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, name + ".csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "module", "test", "expected", "actual", "status", "ms"])
        w.writeheader()
        w.writerows(results)
    with open(os.path.join(here, name + ".md"), "w", encoding="utf-8") as f:
        f.write("# Brews & Blessings - API test results\n\n")
        f.write(f"- Date: {ran:%Y-%m-%d %H:%M}\n- Server: {BASE}\n")
        f.write(f"- Passed: {counts['PASS']}  Failed: {counts['FAIL']}  Skipped: {counts['SKIP']}  Total: {total}\n\n")
        f.write("| ID | Module | Test | Expected | Actual | Status |\n|---|---|---|---|---|---|\n")
        for r in results:
            cells = [r["id"], r["module"], r["test"], r["expected"], r["actual"], r["status"]]
            f.write("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |\n")
    print(f"Report saved: {name}.csv and {name}.md in the backend folder")
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
