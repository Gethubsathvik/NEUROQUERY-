"""Pick a sensible chart type from a query result."""
from __future__ import annotations

import re

DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def suggest_chart(columns: list[str], rows: list[list]) -> dict:
    if not rows or not columns:
        return {"type": "table"}

    numeric = [
        i for i in range(len(columns))
        if any(_is_num(r[i]) for r in rows) and all(_is_num(r[i]) or r[i] is None for r in rows)
    ]
    labels = [i for i in range(len(columns)) if i not in numeric]

    if len(rows) == 1 and numeric and not labels:
        return {"type": "metric"}
    if not numeric or not labels:
        return {"type": "table"}

    x = labels[0]
    ys = [columns[i] for i in numeric[:3]]
    is_time = len(rows) >= 2 and all(isinstance(r[x], str) and DATE_RE.match(r[x]) for r in rows)
    if is_time:
        return {"type": "line", "x": columns[x], "y": ys}
    if len(rows) <= 25:
        return {"type": "bar", "x": columns[x], "y": ys}
    return {"type": "table"}
