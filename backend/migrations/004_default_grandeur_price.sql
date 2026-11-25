-- Repair-safe catalog price migration. This also covers databases where an
-- earlier bootstrap recorded migration 003 before running its SQL.
BEGIN;

ALTER TABLE product ADD COLUMN IF NOT EXISTS grandeurprice NUMERIC(10,2);
ALTER TABLE product ADD COLUMN IF NOT EXISTS hotprice NUMERIC(10,2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discountnote VARCHAR(60);

UPDATE product AS p
SET grandeurprice = v.grandeur,
    hotprice = v.hot
FROM (VALUES
    ('Americano', 110, 60), ('Cafe Latte', 150, 110),
    ('Caramel Latte', 150, 115), ('Caramel Macchiato', 160, 125),
    ('Caramelized Mocha', 160, 125), ('Dirty Matcha', 160, 125),
    ('Hazelnut Latte', 150, 115), ('Salted Caramel Latte', 150, 115),
    ('Spanish Latte', 160, 125), ('Tres Leche Latte', 160, 125),
    ('White Mocha Latte', 160, 125), ('Biscoff Latte', 205, 160),
    ('Blueberry Milk', 140, 105), ('Caramel Milk', 140, 105),
    ('Chocolate Milk', 140, 105), ('Strawberry Milk', 140, 105),
    ('Oreo Milk', 140, 105), ('Matcha Milk', 150, 115),
    ('Strawberry Matcha', 150, 115), ('Strawberry Cocoa', 150, 115),
    ('Milky Berry Oreo', 150, 115), ('Blueberry Fizz', 89, NULL),
    ('Green Apple Fizz', 89, NULL), ('Lychee Fizz', 89, NULL),
    ('Mango Fizz', 89, NULL), ('Strawberry Fizz', 89, NULL),
    ('Passion Fruit Fizz', 89, NULL), ('Mango Passion', 140, NULL),
    ('Paradise Coconut', 170, NULL), ('Pink Berry Drink', 170, NULL)
) AS v(name, grandeur, hot)
WHERE lower(p.productname) = lower(v.name);

UPDATE product SET grandeurprice = sellingprice WHERE grandeurprice IS NULL;

COMMIT;
