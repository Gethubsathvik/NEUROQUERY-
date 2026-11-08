"""Execution-accuracy evaluation harness for the NL-to-SQL engine.

For every golden case, the generated SQL and the reference SQL are both executed and
their result sets compared (order-insensitive, floats rounded). Run it with:

    python -m app.evaluate
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from .db import Database, QueryError
from .llm import GenerationError, NoAnswer, get_generator
from .safety import UnsafeSQLError, validate_sql

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden.json"


def _normalize(rows: list[list]) -> list[tuple]:
    def norm(v):
        return round(v, 2) if isinstance(v, float) else v
    return sorted((tuple(norm(v) for v in r) for r in rows), key=lambda t: [str(x) for x in t])


def run_eval(db: Database, generator, cases: list[dict]) -> dict:
    schema_text, allowed = db.schema_text(), db.table_names()
    results = []
    for case in cases:
        entry = {"question": case["question"], "passed": False, "error": None}
        try:
            expected = db.run_query(case["reference_sql"], max_rows=10_000)
            generated = generator.generate(case["question"], schema_text)
            safe = validate_sql(generated.sql, allowed)
            actual = db.run_query(safe, max_rows=10_000)
            entry["passed"] = _normalize(actual["rows"]) == _normalize(expected["rows"])
            if not entry["passed"]:
                entry["error"] = "result set differs from reference"
            entry["generated_sql"] = safe
        except (NoAnswer, GenerationError, UnsafeSQLError, QueryError) as e:
            entry["error"] = f"{e.__class__.__name__}: {e}"
        results.append(entry)
    passed = sum(r["passed"] for r in results)
    return {
        "engine": generator.name,
        "total": len(results),
        "passed": passed,
        "execution_accuracy": round(100 * passed / len(results), 1) if results else 0.0,
        "cases": results,
    }


def main() -> int:
    cases = json.loads(GOLDEN_PATH.read_text())
    generator = get_generator()
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "eval.db")
        db.ensure_seeded()
        report = run_eval(db, generator, cases)
    out = GOLDEN_PATH.parent / "report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"Engine: {report['engine']}")
    for c in report["cases"]:
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['question']}" + (f"  ({c['error']})" if c["error"] else ""))
    print(f"Execution accuracy: {report['passed']}/{report['total']} = {report['execution_accuracy']}%")
    print(f"Report written to {out}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
