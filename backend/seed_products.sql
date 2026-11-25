-- ============================================================
-- seed_products.sql
-- The full menu from the Settings page (30 products).
-- Skips any product whose name already exists, so it is safe to run again.
-- (The 5 products from seed_transactions.sql keep their existing prices.)
-- Run AFTER schema.sql. Prices can be edited later on the Settings page.
-- ============================================================

INSERT INTO Product (ProductName, Category, SellingPrice, PackagingCost, IsAvailable)
SELECT v.name, v.cat::product_category, v.price, v.pkg, v.avail
FROM (VALUES
    ('Americano', 'Coffee', 80, 8, true),
    ('Cafe Latte', 'Coffee', 120, 8, true),
    ('Caramel Latte', 'Coffee', 120, 8, true),
    ('Caramel Macchiato', 'Coffee', 130, 8, true),
    ('Caramelized Mocha', 'Coffee', 130, 8, true),
    ('Dirty Matcha', 'Coffee', 130, 8, true),
    ('Hazelnut Latte', 'Coffee', 120, 8, true),
    ('Salted Caramel Latte', 'Coffee', 120, 8, true),
    ('Spanish Latte', 'Coffee', 130, 8, true),
    ('Tres Leche Latte', 'Coffee', 130, 8, true),
    ('White Mocha Latte', 'Coffee', 130, 8, true),
    ('Biscoff Latte', 'Coffee', 165, 8, true),
    ('Blueberry Milk', 'Non-Coffee', 110, 8, true),
    ('Caramel Milk', 'Non-Coffee', 110, 8, true),
    ('Chocolate Milk', 'Non-Coffee', 110, 8, true),
    ('Strawberry Milk', 'Non-Coffee', 110, 8, true),
    ('Oreo Milk', 'Non-Coffee', 110, 8, true),
    ('Matcha Milk', 'Non-Coffee', 120, 8, true),
    ('Strawberry Matcha', 'Non-Coffee', 120, 8, true),
    ('Strawberry Cocoa', 'Non-Coffee', 120, 8, true),
    ('Milky Berry Oreo', 'Non-Coffee', 120, 8, true),
    ('Blueberry Fizz', 'Refreshers', 69, 8, true),
    ('Green Apple Fizz', 'Refreshers', 69, 8, true),
    ('Lychee Fizz', 'Refreshers', 69, 8, true),
    ('Mango Fizz', 'Refreshers', 69, 8, true),
    ('Strawberry Fizz', 'Refreshers', 69, 8, true),
    ('Passion Fruit Fizz', 'Refreshers', 69, 8, true),
    ('Mango Passion', 'Refreshers', 110, 8, true),
    ('Paradise Coconut', 'Refreshers', 140, 8, true),
    ('Pink Berry Drink', 'Refreshers', 140, 8, true)
) AS v(name, cat, price, pkg, avail)
WHERE NOT EXISTS (SELECT 1 FROM Product p WHERE lower(p.ProductName) = lower(v.name));
