import pytest

from app.charts import suggest_chart
from app.db import CSVImportError, Database, QueryError, QueryTimeout


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "t.db")
    d.ensure_seeded()
    return d


def test_seed_creates_expected_tables(db):
    names = db.table_names()
    assert names == ["customers", "order_items", "orders", "products"]
    counts = {t["name"]: t["row_count"] for t in db.schema()}
    assert counts["customers"] == 250 and counts["orders"] == 2600 and counts["order_items"] > 2600


def test_schema_text_mentions_tables_and_values(db):
    text = db.schema_text()
    assert "Table orders" in text and "completed" in text and "FK:" in text


def test_row_cap_and_truncation(db):
    res = db.run_query("SELECT * FROM orders", max_rows=10)
    assert res["row_count"] == 10 and res["truncated"] is True


def test_authorizer_blocks_writes_and_system_tables(db):
    for sql in ["DELETE FROM orders", "DROP TABLE orders", "SELECT * FROM sqlite_master"]:
        with pytest.raises(QueryError):
            db.run_query(sql)
    assert db.run_query("SELECT COUNT(*) FROM orders")["rows"][0][0] == 2600


def test_cte_queries_run_but_cannot_reach_system_tables(db):
    ok = db.run_query("WITH t AS (SELECT status, COUNT(*) n FROM orders GROUP BY 1) SELECT * FROM t ORDER BY n DESC")
    assert ok["row_count"] == 4
    with pytest.raises(QueryError):
        db.run_query("WITH t AS (SELECT * FROM sqlite_master) SELECT * FROM t")


def test_timeout(db):
    sql = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(QueryTimeout):
        db.run_query(sql, timeout_s=0.2)


def test_csv_import_infers_types_and_is_queryable(db):
    csv_bytes = b"Name,Age,Score\nAsha,30,4.5\nRavi,25,3.8\n"
    info = db.import_csv("My Data.csv", csv_bytes)
    assert info["table"] == "my_data" and info["columns"] == {"name": "TEXT", "age": "INTEGER", "score": "REAL"}
    assert db.run_query("SELECT AVG(age) FROM my_data")["rows"][0][0] == 27.5


def test_csv_import_rejects_bad_files(db):
    with pytest.raises(CSVImportError):
        db.import_csv("x.csv", b"only,header\n")
    with pytest.raises(CSVImportError):
        db.import_csv("customers.csv", b"a\n1\n")  # table exists
    with pytest.raises(CSVImportError):
        db.import_csv("big.csv", b"a\n" + b"1\n" * 10, max_bytes=5)


def test_chart_suggestions():
    assert suggest_chart(["n"], [[5]])["type"] == "metric"
    assert suggest_chart(["month", "rev"], [["2024-01", 1], ["2024-02", 2]])["type"] == "line"
    assert suggest_chart(["cat", "rev"], [["a", 1], ["b", 2]])["type"] == "bar"
    assert suggest_chart(["a", "b"], [["x", "y"]])["type"] == "table"
    assert suggest_chart(["a"], [])["type"] == "table"
