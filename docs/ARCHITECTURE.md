# 🏗️ ARCHITECTURE: NEUROQUERY

## 1. 🔭 Overview
A single FastAPI service serves a JSON API and a static single-page UI. SQL generation is
pluggable (LLM API or offline demo engine). All generated SQL goes through the same
validation and hardened execution path.

```
Browser (static/index.html, vanilla JS + Chart.js)
        │  fetch JSON
        ▼
FastAPI (app/main.py)
  /api/ask ─► schema_text()        (app/db.py)
           ─► Generator.generate() (app/llm.py: LLM | Demo)
           ─► validate_sql()       (app/safety.py, sqlglot AST)
           ─► Database.run_query() (app/db.py: read-only + authorizer + cap + timeout)
           ─► suggest_chart()      (app/charts.py)
           ─► History.add()        (app/history.py)
        on QueryError (once): Generator.repair() ─► validate ─► run
        ▼
SQLite files in NEUROQUERY_DATA_DIR:  neuroquery.db (data)   history.db (query log)
```

## 2. 🧩 Components
| Module | Responsibility |
|---|---|
| `app/main.py` | 🌐 `create_app()` factory, endpoints, error-to-HTTP mapping, static hosting |
| `app/llm.py` | 🤖 `GeneratedSQL`, `NoAnswer`, `GenerationError`, `DemoGenerator`, `LLMGenerator`, `get_generator()` |
| `app/safety.py` | 🛡️ `validate_sql()` and `UnsafeSQLError`: static analysis with sqlglot |
| `app/db.py` | 🗄️ `Database`: seeding, schema + `schema_text()`, `run_query()`, `import_csv()`; authorizer |
| `app/seed.py` | 🌱 Deterministic sample e-commerce data (random seed 42) |
| `app/charts.py` | 📈 `suggest_chart(columns, rows)` |
| `app/history.py` | 🕘 Persistent history in a separate SQLite file |
| `app/evaluate.py` | 📊 Execution-accuracy harness; CLI `python -m app.evaluate` |
| `static/index.html` | 🖥️ Entire UI (HTML, CSS, JS in one file) |
| `eval/golden.json` | 🧪 Golden question + reference SQL pairs |

## 3. 🔄 Request flow for `POST /api/ask`
1. Validate request (1 to 500 chars, at least 3 after trim, else 422).
2. Build `schema_text` (tables, columns, PK, FKs, values of columns with ≤ 8 distinct short strings, row counts, business notes).
3. `generate(question, schema_text)` returns `GeneratedSQL(sql, explanation)`.
   - `NoAnswer` → 422 with reason. `GenerationError` → 502.
4. `validate_sql(sql, allowed_tables)`. `UnsafeSQLError` → 400, no repair.
5. `run_query(sql, max_rows, timeout)`.
   - `QueryTimeout` → 408.
   - `QueryError` → one `repair()` attempt with the SQLite error, then re-validate and re-run; a second failure → 422.
6. Save to history, build chart suggestion, return payload.

## 4. 🛡️ Safety layers
| Layer | Where | What it stops |
|---|---|---|
| 1. AST validation | `safety.py` | Multiple statements, non-SELECT, DDL/DML, PRAGMA/ATTACH, unknown tables, table-valued functions, `load_extension` and similar functions |
| 2. Read-only connection | `db._ro()` (`mode=ro`) | Any write at the SQLite level |
| 3. Authorizer | `db._make_authorizer()` | Everything except SELECT/recursive and reads on allow-listed tables. Reads that report no database name (CTEs, subqueries) are allowed; reads of real tables outside the allow-list (e.g. `sqlite_master`) are denied |
| 4. Resource limits | `db.run_query()` | Row cap via `fetchmany(max+1)`; timeout via `set_progress_handler` every 1000 VM steps |

## 5. 🗃️ Data model
Sample database (seeded on first start):
```
customers(id PK, name, country, segment, signup_date)          250 rows
products(id PK, name, category, price)                          24 rows
orders(id PK, customer_id → customers.id, order_date, status)  2600 rows
order_items(id PK, order_id → orders.id, product_id → products.id, quantity, unit_price)  ~6.5k rows
```
Conventions: dates are ISO text; statuses are `completed | cancelled | refunded | pending`;
**revenue = SUM(quantity × unit_price) for `status = 'completed'`**.

Uploaded CSVs become new tables: names and columns sanitized to `[a-z0-9_]`, types inferred
(INTEGER, REAL, TEXT), limits 5 MB and 100,000 rows, existing table names rejected.

History table: `history(id, question, sql, row_count, engine, created_at)` in `history.db`.

## 6. 🔌 API
| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{status, engine}` |
| GET | `/api/schema` | tables with columns, PK flags, foreign keys, row counts |
| GET | `/api/examples` | example questions and active engine |
| GET | `/api/history?limit=` | 1 to 100 items, newest first |
| POST | `/api/upload` | multipart `file` (.csv) returns `{table, rows, columns}`; 400 on bad input |
| POST | `/api/ask` | `{"question": "..."}` returns `{question, sql, explanation, engine, attempts, chart, columns, rows, row_count, truncated, elapsed_ms}` |
| GET | `/` and `/static/*` | UI |

Error mapping: 400 unsafe SQL or bad upload · 408 timeout · 422 unanswerable, too short, or SQL failed after repair · 502 LLM call failed.

## 7. 📈 Chart selection rules (`charts.py`)
- 1 row, all numeric → `metric` cards.
- Needs ≥ 1 numeric column and ≥ 1 label column, else `table`.
- First label column is X; up to 3 numeric columns are series.
- ≥ 2 rows and X values all match `YYYY-MM` or `YYYY-MM-DD` → `line`.
- ≤ 25 rows → `bar`; otherwise `table`.

## 8. ⚙️ Configuration (environment)
| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | unset | Enables the LLM engine |
| `LLM_API_URL` | provider default (chat-completions style) | Override the LLM HTTP endpoint |
| `NEUROQUERY_MODEL` | `gpt-4o-mini` | Model used for generation and repair |
| `NEUROQUERY_ENGINE` | unset | `demo` forces the offline engine |
| `NEUROQUERY_DATA_DIR` | `./data` | Location of `neuroquery.db` and `history.db` |
| `NEUROQUERY_MAX_ROWS` | 500 | Row cap per query |
| `NEUROQUERY_QUERY_TIMEOUT` | 3 | Seconds |

## 9. 🧠 Key decisions
| Decision | Reason |
|---|---|
| Pluggable generator with a shared interface | Same pipeline for demo, tests and LLM; easy to add providers |
| Offline demo engine | Zero-setup demos and deterministic CI without network or keys |
| sqlglot AST validation instead of regex | Robust against comments, casing and nesting tricks |
| Defense in depth (validator + read-only + authorizer + limits) | No single layer is trusted |
| Never repair unsafe SQL | Avoids letting an attacker iterate against the validator |
| Raw `httpx` HTTP call to the LLM API | Small dependency footprint, provider-configurable |
| SQLite and single-file UI | Fast to run, fork and demo; trade-off is no multi-user or scale features |
| `create_app()` factory | Tests get isolated data dirs and injected generators |

## 10. ✅ Testing and evaluation
- `tests/test_safety.py`: allowed and blocked SQL matrix.
- `tests/test_db.py`: seeding, row cap, authorizer, CTE handling, timeout, CSV import, chart rules.
- `tests/test_api.py`: endpoints, unsafe SQL blocked, repair loop, upload, history.
- `tests/test_eval.py`: harness passes golden set with demo engine and detects a wrong engine.
- `python -m app.evaluate` writes `eval/report.json` (execution accuracy).

## 11. 🚀 Deployment
`Dockerfile` runs `uvicorn app.main:app` on port 8000 with `NEUROQUERY_DATA_DIR=/srv/data`.
Mount a volume at `/srv/data` for persistence. Add authentication before exposing publicly.

## 12. ⚠️ Known limitations
No authentication; one shared database and history; uploaded tables cannot be deleted from the UI;
demo engine understands a fixed set of questions; Chart.js loads from a CDN; SQLite only.

## 13. 🔁 Three-Cycle Live Proof (architecture view)
- **Cycle 1 (safety/correctness):** validator + authorizer + read-only + limits verified by `pytest`.
- **Cycle 2 (live flow):** browser → API → generator → validate → execute → chart/history path exercised on running server.
- **Cycle 3 (accuracy):** evaluation harness compares generated vs reference result sets; record in `MEMORY.md`.
