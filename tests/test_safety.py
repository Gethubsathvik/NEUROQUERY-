import pytest

from app.safety import UnsafeSQLError, validate_sql

TABLES = {"customers", "orders", "order_items", "products"}


@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",
    "SELECT COUNT(*) FROM orders;",
    "WITH t AS (SELECT customer_id, COUNT(*) n FROM orders GROUP BY 1) SELECT * FROM t WHERE n > 2",
    "SELECT name FROM customers UNION SELECT name FROM products",
    "SELECT c.name FROM customers c JOIN orders o ON o.customer_id = c.id LIMIT 3",
])
def test_allows_read_only_queries(sql):
    assert validate_sql(sql, TABLES)


@pytest.mark.parametrize("sql", [
    "DROP TABLE orders",
    "DELETE FROM orders",
    "UPDATE customers SET name = 'x'",
    "INSERT INTO customers VALUES (1,'a','b','c','d')",
    "SELECT 1; DROP TABLE orders",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM secrets",
    "PRAGMA table_info(orders)",
    "ATTACH DATABASE 'x.db' AS x",
    "SELECT load_extension('evil')",
    "SELECT * FROM pragma_table_info('orders')",
    "CREATE TABLE x (a INT)",
    "",
    "   ",
    "SELEC nonsense ((",
])
def test_blocks_unsafe_queries(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql, TABLES)
