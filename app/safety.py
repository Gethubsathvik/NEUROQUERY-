"""SQL safety validator. Only a single read-only query over known tables is allowed.

This is layer 1 (static analysis). Layer 2 lives in db.py: a read-only SQLite
connection, an authorizer that only permits reads on allow-listed tables,
a row cap and a query timeout.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

QUERY_TYPES = tuple(
    getattr(exp, n) for n in ("Select", "Union", "Intersect", "Except", "Subquery") if hasattr(exp, n)
)
DENY_NODES = {
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Pragma", "Attach",
    "Detach", "Merge", "TruncateTable", "Set", "Use", "Transaction", "Commit", "Rollback",
    "Copy", "LoadData", "Into",
}
DENY_FUNCS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer", "zipfile"}


class UnsafeSQLError(ValueError):
    """Raised when SQL is not a single, read-only query over allowed tables."""


def validate_sql(sql: str, allowed_tables: set[str] | list[str]) -> str:
    """Return the cleaned SQL if it is safe, otherwise raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("empty query")
    cleaned = sql.strip().rstrip(";").strip()
    allowed = {t.lower() for t in allowed_tables}

    try:
        statements = [s for s in sqlglot.parse(cleaned, read="sqlite") if s is not None]
    except ParseError as e:
        raise UnsafeSQLError(f"could not parse SQL: {str(e)[:120]}") from e

    if len(statements) != 1:
        raise UnsafeSQLError("exactly one statement is allowed")
    stmt = statements[0]
    if not isinstance(stmt, QUERY_TYPES):
        raise UnsafeSQLError("only SELECT queries are allowed")

    for node in stmt.walk():
        if type(node).__name__ in DENY_NODES:
            raise UnsafeSQLError(f"{type(node).__name__.upper()} is not allowed")
        if isinstance(node, exp.Anonymous) and node.name.lower() in DENY_FUNCS:
            raise UnsafeSQLError(f"function {node.name} is not allowed")

    cte_names = {c.alias.lower() for c in stmt.find_all(exp.CTE) if c.alias}
    for table in stmt.find_all(exp.Table):
        if not table.name or isinstance(table.this, exp.Func):
            raise UnsafeSQLError("table-valued functions are not allowed")
        name = table.name.lower()
        if name in cte_names:
            continue
        if name not in allowed:
            raise UnsafeSQLError(f"unknown or restricted table '{table.name}'")
    return cleaned
