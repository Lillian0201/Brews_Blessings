-- ============================================================
-- seed_transactions.sql
-- Sample data for testing the Transactions page.
-- Run AFTER schema.sql and migrations/001_transactions.sql.
-- Safe to run more than once (skips if the T-orders already exist).
-- NOTE: the passwords below are NOT real hashes. Real login comes later.
-- ============================================================

INSERT INTO "User" (FullName, Username, Password, Role)
VALUES
    ('Owner',   'owner',   'CHANGE_ME', 'Owner'),
    ('Barista', 'barista', 'CHANGE_ME', 'Barista')
ON CONFLICT (Username) DO NOTHING;

INSERT INTO Product (ProductName, Category, SellingPrice, ProductCost)
SELECT v.name, v.cat::product_category, v.price, v.cost
FROM (VALUES
    ('Spanish Latte', 'Coffee', 180, 60),
    ('Cafe Latte',    'Coffee', 150, 50),
    ('Mocha Latte',   'Coffee', 165, 55),
    ('Americano',     'Coffee', 110, 30),
    ('Matcha Milk',   'Non-Coffee', 130, 45)
) AS v(name, cat, price, cost)
WHERE NOT EXISTS (SELECT 1 FROM Product p WHERE p.ProductName = v.name);

DO $$
DECLARE
    owner_id   INT := (SELECT UserID FROM "User" WHERE Username = 'owner');
    barista_id INT := (SELECT UserID FROM "User" WHERE Username = 'barista');
    o1 INT; o2 INT; o3 INT; o4 INT; o5 INT;
BEGIN
    IF EXISTS (SELECT 1 FROM Orders WHERE OrderNumber LIKE 'T0%') THEN
        RAISE NOTICE 'Transaction seed data already exists, skipping.';
        RETURN;
    END IF;

    -- T001: plain completed sale (Cash)
    INSERT INTO Orders (UserID, OrderNumber, CustomerName, TotalAmount, PaymentMethod, AmountTendered, OrderDateTime, OrderStatus)
    VALUES (barista_id, 'T001', 'Anna', 180, 'Cash', 200, CURRENT_TIMESTAMP - INTERVAL '3 hours', 'Completed')
    RETURNING OrderID INTO o1;
    INSERT INTO OrderItem (OrderID, ProductID, ItemName, Quantity, UnitPrice, Customization)
    VALUES (o1, (SELECT ProductID FROM Product WHERE ProductName='Spanish Latte'), 'Spanish Latte', 1, 180, 'Classic · 1 Shot · Sweetness 50%');

    -- T002: sale that was refunded (approved refund below)
    INSERT INTO Orders (UserID, OrderNumber, CustomerName, TotalAmount, PaymentMethod, AmountTendered, OrderDateTime, OrderStatus)
    VALUES (barista_id, 'T002', 'Ben', 150, 'Cash', 150, CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Refunded')
    RETURNING OrderID INTO o2;
    INSERT INTO OrderItem (OrderID, ProductID, ItemName, Quantity, UnitPrice)
    VALUES (o2, (SELECT ProductID FROM Product WHERE ProductName='Cafe Latte'), 'Cafe Latte', 1, 150);
    INSERT INTO Refund (OrderID, ApprovedBy, RefundAmount, Reason, ItemReturned, Status, RequestedBy, ItemName, ApprovedAt)
    VALUES (o2, owner_id, 150, 'Wrong drink served', FALSE, 'Approved', barista_id, 'Cafe Latte', CURRENT_TIMESTAMP - INTERVAL '1 hour');

    -- T003: voided sale
    INSERT INTO Orders (UserID, OrderNumber, CustomerName, TotalAmount, PaymentMethod, OrderDateTime, OrderStatus, VoidReason, VoidedBy, VoidedAt)
    VALUES (barista_id, 'T003', 'Carla', 165, 'Cash', CURRENT_TIMESTAMP - INTERVAL '90 minutes', 'Voided',
            'Customer left before paying', owner_id, CURRENT_TIMESTAMP - INTERVAL '80 minutes')
    RETURNING OrderID INTO o3;
    INSERT INTO OrderItem (OrderID, ProductID, ItemName, Quantity, UnitPrice)
    VALUES (o3, (SELECT ProductID FROM Product WHERE ProductName='Mocha Latte'), 'Mocha Latte', 1, 165);

    -- T004: two items, discount 30, GCash. Subtotal 110*2 + 130 = 350, total 320
    INSERT INTO Orders (UserID, OrderNumber, CustomerName, DiscountAmount, TotalAmount, PaymentMethod, AmountTendered, OrderDateTime, OrderStatus)
    VALUES (barista_id, 'T004', 'Diego', 30, 320, 'GCash', 320, CURRENT_TIMESTAMP - INTERVAL '45 minutes', 'Completed')
    RETURNING OrderID INTO o4;
    INSERT INTO OrderItem (OrderID, ProductID, ItemName, Quantity, UnitPrice)
    VALUES (o4, (SELECT ProductID FROM Product WHERE ProductName='Americano'), 'Americano', 2, 110),
           (o4, (SELECT ProductID FROM Product WHERE ProductName='Matcha Milk'), 'Matcha Milk', 1, 130);

    -- T005: completed sale with a refund request waiting for approval
    INSERT INTO Orders (UserID, OrderNumber, CustomerName, TotalAmount, PaymentMethod, AmountTendered, OrderDateTime, OrderStatus)
    VALUES (barista_id, 'T005', 'Eli', 130, 'Cash', 200, CURRENT_TIMESTAMP - INTERVAL '20 minutes', 'Completed')
    RETURNING OrderID INTO o5;
    INSERT INTO OrderItem (OrderID, ProductID, ItemName, Quantity, UnitPrice)
    VALUES (o5, (SELECT ProductID FROM Product WHERE ProductName='Matcha Milk'), 'Matcha Milk', 1, 130);
    INSERT INTO Refund (OrderID, RefundAmount, Reason, ItemReturned, Status, RequestedBy, ItemName)
    VALUES (o5, 130, 'Spilled by staff', FALSE, 'Pending', barista_id, 'Matcha Milk');
END
$$;
