-- ============================================================
-- cleanup_test_data.sql
-- Removes everything that api_tests.py created. It only touches rows
-- whose name or description starts with AUTOTEST (or a username that
-- starts with autotest), so your real data is not affected.
-- Run it in pgAdmin (Query Tool) after you run the tests.
-- ============================================================
BEGIN;

-- Orders made by the tests (customer name AUTOTEST ...), and what hangs off them
DELETE FROM refund
 WHERE orderid IN (SELECT orderid FROM orders WHERE customername LIKE 'AUTOTEST%');
DELETE FROM stockmovement
 WHERE orderid IN (SELECT orderid FROM orders WHERE customername LIKE 'AUTOTEST%');
DELETE FROM orders WHERE customername LIKE 'AUTOTEST%';      -- order items go with them

-- Expenses
DELETE FROM expense WHERE description LIKE 'AUTOTEST%';

-- Inventory items, their batches and movements
DELETE FROM stockmovement
 WHERE ingredientid IN (SELECT ingredientid FROM ingredient WHERE name LIKE 'AUTOTEST%');
DELETE FROM stockbatch
 WHERE ingredientid IN (SELECT ingredientid FROM ingredient WHERE name LIKE 'AUTOTEST%');
DELETE FROM recipe
 WHERE ingredientid IN (SELECT ingredientid FROM ingredient WHERE name LIKE 'AUTOTEST%');
DELETE FROM ingredient WHERE name LIKE 'AUTOTEST%';

-- Products and users
DELETE FROM product WHERE productname LIKE 'AUTOTEST%';
DELETE FROM "User" WHERE username LIKE 'autotest%';

COMMIT;

-- Check that nothing is left (all four should return 0):
SELECT COUNT(*) AS orders_left   FROM orders     WHERE customername LIKE 'AUTOTEST%';
SELECT COUNT(*) AS products_left FROM product    WHERE productname  LIKE 'AUTOTEST%';
SELECT COUNT(*) AS expenses_left FROM expense    WHERE description  LIKE 'AUTOTEST%';
SELECT COUNT(*) AS users_left    FROM "User"     WHERE username     LIKE 'autotest%';
