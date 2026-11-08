"""SQLite access: schema introspection, hardened read-only execution, CSV import."""
from __future__ import annotations

import csv
import io
import re
import sqlite3
import time
from pathlib import Path

from . import seed

DENY_FUNCS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}
SQLITE_RECURSIVE = getattr(sqlite3, "SQLITE_RECURSIVE", 33)

BUSINESS_NOTES = (
    "Notes for the sample tables: dates are ISO text (YYYY-MM-DD). Revenue means "
    "SUM(order_items.quantity * order_items.unit_price) for orders with status = 'completed'. "
    "Use strftime('%Y-%m', order_date) for monthly grouping."
)


class QueryError(Exception):
    """The query failed to run (bad column, syntax, blocked by the authorizer...)."""


class QueryTimeout(QueryError):
    """The query exceeded the time limit."""


class CSVImportError(ValueError):
    """The uploaded CSV could not be imported."""


def _make_authorizer(allowed: set[str]):
    def authorizer(action, arg1, arg2, dbname, source):
        if action in (sqlite3.SQLITE_SELECT, SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            # Reads of CTEs/subqueries report no database name; real tables report "main"/"temp".
            if not arg1 or not dbname or arg1.lower() in allowed:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_DENY if (arg2 or "").lower() in DENY_FUNCS else sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    return authorizer


def _json_safe(value):
    if isinstance(value, (bytes, bytearray)):
        return f"<blob {len(value)} bytes>"
    return value


def _sanitize(name: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_") or fallback
    return f"c_{s}" if s[0].isdigit() else s


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    # ---- setup ---------------------------------------------------------
    def ensure_seeded(self) -> None:
        if not self.path.exists():
            seed.build(self.path)

    def _ro(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)

    # ---- schema --------------------------------------------------------
    def table_names(self) -> list[str]:
        conn = self._ro()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        finally:
            conn.close()
        return [r[0] for r in rows]

    def schema(self) -> list[dict]:
        conn = self._ro()
        try:
            out = []
            for name in self.table_names():
                cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
                count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                fks = conn.execute(f'PRAGMA foreign_key_list("{name}")').fetchall()
                out.append({
                    "name": name,
                    "row_count": count,
                    "columns": [{"name": c[1], "type": c[2] or "TEXT", "pk": bool(c[5])} for c in cols],
                    "foreign_keys": [{"column": f[3], "ref_table": f[2], "ref_column": f[4]} for f in fks],
                })
            return out
        finally:
            conn.close()

    def schema_text(self) -> str:
        conn = self._ro()
        lines = []
        try:
            for t in self.schema():
                col_parts = []
                for c in t["columns"]:
                    part = f'{c["name"]} {c["type"]}' + (" PK" if c["pk"] else "")
                    if c["type"].upper() == "TEXT":
                        vals = [r[0] for r in conn.execute(
                            f'SELECT DISTINCT "{c["name"]}" FROM "{t["name"]}" LIMIT 9').fetchall()]
                        if 0 < len(vals) <= 8 and all(isinstance(v, str) and len(v) < 30 for v in vals):
                            part += " values=" + "|".join(sorted(vals))
                    col_parts.append(part)
                line = f'Table {t["name"]} ({", ".join(col_parts)}) -- {t["row_count"]} rows'
                if t["foreign_keys"]:
                    fk = ", ".join(f'{f["column"]} -> {f["ref_table"]}.{f["ref_column"]}' for f in t["foreign_keys"])
                    line += f"; FK: {fk}"
                lines.append(line)
        finally:
            conn.close()
        lines.append(BUSINESS_NOTES)
        return "\n".join(lines)

    # ---- query execution ----------------------------------------------
    def run_query(self, sql: str, max_rows: int = 500, timeout_s: float = 3.0) -> dict:
        allowed = {t.lower() for t in self.table_names()}
        conn = self._ro()
        deadline = time.monotonic() + timeout_s
        state = {"timed_out": False}

        def progress() -> int:
            if time.monotonic() > deadline:
                state["timed_out"] = True
                return 1
            return 0

        conn.set_progress_handler(progress, 1000)
        conn.set_authorizer(_make_authorizer(allowed))
        start = time.perf_counter()
        try:
            cur = conn.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            fetched = cur.fetchmany(max_rows + 1)
        except sqlite3.Error as e:
            if state["timed_out"]:
                raise QueryTimeout(f"query exceeded {timeout_s:g}s") from e
            raise QueryError(str(e)) from e
        finally:
            conn.close()
        truncated = len(fetched) > max_rows
        rows = [[_json_safe(v) for v in r] for r in fetched[:max_rows]]
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 1),
        }

    # ---- CSV import ----------------------------------------------------
    def import_csv(self, filename: str, data: bytes, max_bytes: int = 5_000_000,
                   max_rows: int = 100_000) -> dict:
        if len(data) > max_bytes:
            raise CSVImportError(f"file is larger than {max_bytes // 1_000_000} MB")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise CSVImportError("file must be UTF-8 encoded CSV") from e
        rows = list(csv.reader(io.StringIO(text)))
        rows = [r for r in rows if any(cell.strip() for cell in r)]
        if len(rows) < 2:
            raise CSVImportError("CSV needs a header row and at least one data row")

        header, body = rows[0], rows[1:max_rows + 1]
        cols, seen = [], set()
        for i, h in enumerate(header):
            base = _sanitize(h, f"col_{i + 1}")
            name, n = base, 2
            while name in seen:
                name, n = f"{base}_{n}", n + 1
            seen.add(name)
            cols.append(name)

        width = len(cols)
        body = [(r + [""] * width)[:width] for r in body]
        types = []
        for i in range(width):
            vals = [r[i].strip() for r in body if r[i].strip()]
            if vals and all(re.fullmatch(r"[+-]?\d+", v) for v in vals):
                types.append("INTEGER")
            elif vals and all(re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", v) for v in vals):
                types.append("REAL")
            else:
                types.append("TEXT")

        table = _sanitize(Path(filename).stem, "uploaded")
        if table.startswith("sqlite_") or table.lower() in {t.lower() for t in self.table_names()}:
            raise CSVImportError(f"a table named '{table}' already exists; rename the file and retry")

        def convert(v: str, t: str):
            v = v.strip()
            if v == "":
                return None
            return int(v) if t == "INTEGER" else float(v) if t == "REAL" else v

        converted = [[convert(r[i], types[i]) for i in range(width)] for r in body]
        ddl = ", ".join(f'"{c}" {t}' for c, t in zip(cols, types))
        conn = sqlite3.connect(self.path)
        try:
            with conn:
                conn.execute(f'CREATE TABLE "{table}" ({ddl})')
                conn.executemany(
                    f'INSERT INTO "{table}" VALUES ({",".join("?" * width)})', converted)
        finally:
            conn.close()
        return {"table": table, "rows": len(converted), "columns": dict(zip(cols, types))}
