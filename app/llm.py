"""Question -> SQL generators.

- LLMGenerator: real NL-to-SQL via an HTTP JSON chat-completions-style API (set LLM_API_KEY).
- DemoGenerator: offline rule-based engine for the sample database, so the app works
  with zero setup and tests run without network access.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

EXAMPLES = [
    "Top 5 customers by revenue",
    "Monthly revenue",
    "Revenue by category",
    "Revenue by country",
    "Orders by status",
    "What is the average order value?",
    "New customers per month",
    "Top 5 products by revenue",
]


@dataclass
class GeneratedSQL:
    sql: str
    explanation: str


class NoAnswer(Exception):
    """The engine cannot answer this question from the available data."""


class GenerationError(Exception):
    """The LLM call itself failed."""


# --------------------------------------------------------------------------- demo
_REV = "SUM(oi.quantity * oi.unit_price)"
_JOIN_ITEMS = "FROM orders o JOIN order_items oi ON oi.order_id = o.id"


def _top_n(q: str) -> int:
    m = re.search(r"top\s*(\d+)", q)
    return max(1, min(int(m.group(1)), 50)) if m else 5


class DemoGenerator:
    name = "demo"

    def generate(self, question: str, schema_text: str) -> GeneratedSQL:
        q = question.lower()

        if re.search(r"(top|best)\s*\d*\s*customers", q):
            n = _top_n(q)
            return GeneratedSQL(
                f"SELECT c.name AS customer, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} JOIN customers c ON c.id = o.customer_id "
                f"WHERE o.status = 'completed' GROUP BY c.id, c.name ORDER BY revenue DESC LIMIT {n}",
                f"Top {n} customers ranked by revenue from completed orders.")
        if re.search(r"(top|best)\s*\d*\s*products", q):
            n = _top_n(q)
            return GeneratedSQL(
                f"SELECT p.name AS product, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} JOIN products p ON p.id = oi.product_id "
                f"WHERE o.status = 'completed' GROUP BY p.id, p.name ORDER BY revenue DESC LIMIT {n}",
                f"Top {n} products ranked by revenue from completed orders.")
        if re.search(r"monthly (revenue|sales)|(revenue|sales) (by|per|each) month|revenue (over time|trend)|sales trend", q):
            return GeneratedSQL(
                f"SELECT strftime('%Y-%m', o.order_date) AS month, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} WHERE o.status = 'completed' GROUP BY month ORDER BY month",
                "Revenue per month from completed orders.")
        if re.search(r"(revenue|sales).*categor|categor.*(revenue|sales)", q):
            return GeneratedSQL(
                f"SELECT p.category AS category, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} JOIN products p ON p.id = oi.product_id "
                f"WHERE o.status = 'completed' GROUP BY p.category ORDER BY revenue DESC",
                "Revenue per product category from completed orders.")
        if re.search(r"(revenue|sales).*countr|countr.*(revenue|sales)", q):
            return GeneratedSQL(
                f"SELECT c.country AS country, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} JOIN customers c ON c.id = o.customer_id "
                f"WHERE o.status = 'completed' GROUP BY c.country ORDER BY revenue DESC",
                "Revenue per customer country from completed orders.")
        if re.search(r"(revenue|sales).*segment|segment.*(revenue|sales)", q):
            return GeneratedSQL(
                f"SELECT c.segment AS segment, ROUND({_REV}, 2) AS revenue "
                f"{_JOIN_ITEMS} JOIN customers c ON c.id = o.customer_id "
                f"WHERE o.status = 'completed' GROUP BY c.segment ORDER BY revenue DESC",
                "Revenue per customer segment from completed orders.")
        if re.search(r"orders?\s*(by|per)\s*status|order status", q):
            return GeneratedSQL(
                "SELECT status, COUNT(*) AS orders FROM orders GROUP BY status ORDER BY orders DESC",
                "Number of orders in each status.")
        if re.search(r"average order value|\baov\b", q):
            return GeneratedSQL(
                "SELECT ROUND(AVG(order_total), 2) AS average_order_value FROM ("
                f"SELECT o.id, {_REV} AS order_total {_JOIN_ITEMS} "
                "WHERE o.status = 'completed' GROUP BY o.id)",
                "Average total value of a completed order.")
        if re.search(r"new customers|signups?|customer growth", q):
            return GeneratedSQL(
                "SELECT strftime('%Y-%m', signup_date) AS month, COUNT(*) AS new_customers "
                "FROM customers GROUP BY month ORDER BY month",
                "Number of customers who signed up each month.")
        if re.search(r"how many customers|number of customers|customer count|total customers", q):
            return GeneratedSQL("SELECT COUNT(*) AS customers FROM customers",
                                "Total number of customers.")
        if re.search(r"how many orders|number of orders|total orders|order count", q):
            return GeneratedSQL("SELECT COUNT(*) AS orders FROM orders", "Total number of orders.")
        if re.search(r"cancel|refund", q):
            return GeneratedSQL(
                "SELECT status, COUNT(*) AS orders, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 1) "
                "AS percent FROM orders WHERE status IN ('cancelled', 'refunded') GROUP BY status",
                "Share of orders that were cancelled or refunded.")
        if re.search(r"total revenue|how much revenue|overall revenue|total sales", q):
            return GeneratedSQL(
                f"SELECT ROUND({_REV}, 2) AS total_revenue {_JOIN_ITEMS} WHERE o.status = 'completed'",
                "Total revenue from completed orders.")

        raise NoAnswer(
            "Demo mode (no LLM_API_KEY set) only understands the sample questions, such as: "
            + "; ".join(EXAMPLES[:5])
            + ". Set LLM_API_KEY (and optionally LLM_API_URL/QUERYX_MODEL) to ask anything about your data."
        )

    def repair(self, question: str, schema_text: str, bad_sql: str, error: str) -> GeneratedSQL:
        raise NoAnswer("The demo engine cannot repair queries.")


# --------------------------------------------------------------------------- llm
SYSTEM_PROMPT = (
    "You are a careful data analyst who writes SQLite queries. "
    "Given a database schema and a question, reply with ONLY a JSON object: "
    '{"sql": "<one SELECT query>", "explanation": "<one plain-English sentence>"}. '
    "Rules: use only tables and columns that appear in the schema; write a single read-only "
    "SELECT (CTEs allowed); never modify data; alias computed columns with readable names; "
    "prefer ORDER BY plus LIMIT for rankings. If the schema cannot answer the question, reply "
    '{"sql": null, "explanation": "<why>"}.'
)


def _parse_json_reply(text: str) -> GeneratedSQL:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise GenerationError("The model did not return JSON.")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise GenerationError("The model returned malformed JSON.") from e
    sql = data.get("sql")
    explanation = str(data.get("explanation", "")).strip()
    if not sql or not isinstance(sql, str):
        raise NoAnswer(explanation or "The question cannot be answered from this data.")
    return GeneratedSQL(sql.strip(), explanation)


class LLMGenerator:
    name = "llm"

    def __init__(self, api_key: str, model: str, api_url: str = DEFAULT_API_URL, timeout: float = 30.0):
        self.api_key, self.model, self.api_url, self.timeout = api_key, model, api_url, timeout

    def _call(self, user_prompt: str) -> GeneratedSQL:
        try:
            r = httpx.post(
                self.api_url,
                headers={"authorization": f"Bearer {self.api_key}", "content-type": "application/json"},
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            raise GenerationError(f"LLM request failed: {e.__class__.__name__}") from e
        if r.status_code != 200:
            raise GenerationError(f"LLM API returned status {r.status_code}")
        try:
            msg = r.json()["choices"][0]["message"]["content"] or ""
        except Exception as e:
            raise GenerationError("LLM API returned an unexpected response shape.") from e
        return _parse_json_reply(msg)

    def generate(self, question: str, schema_text: str) -> GeneratedSQL:
        return self._call(f"Schema:\n{schema_text}\n\nQuestion: {question}")

    def repair(self, question: str, schema_text: str, bad_sql: str, error: str) -> GeneratedSQL:
        return self._call(
            f"Schema:\n{schema_text}\n\nQuestion: {question}\n\n"
            f"Your previous SQL failed.\nSQL: {bad_sql}\nSQLite error: {error}\n"
            "Return a corrected query in the same JSON format."
        )


def get_generator():
    key = os.environ.get("LLM_API_KEY", "").strip()
    if key and os.environ.get("QUERYX_ENGINE", "").lower() != "demo":
        model = os.environ.get("QUERYX_MODEL", "").strip() or DEFAULT_MODEL
        api_url = os.environ.get("LLM_API_URL", "").strip() or DEFAULT_API_URL
        return LLMGenerator(key, model, api_url)
    return DemoGenerator()
