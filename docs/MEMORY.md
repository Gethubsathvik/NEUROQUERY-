# 🧠 MEMORY: NEUROQUERY

Living project memory: context, decisions, gotchas and current state. Read this first when
resuming work; update it whenever you decide something or learn something.

## 1. 🧾 Project in one paragraph
NEUROQUERY is a natural-language-to-SQL BI tool (FastAPI + SQLite + vanilla JS). A question becomes
SQL via an LLM engine (or an offline demo engine), is validated and executed under strict read-only
limits, and returns a table plus an auto-chosen chart. Built as an AI/Data Science portfolio MVP
that emphasizes **🛡️ safety** and **📊 evaluation**.

## 2. 📍 Current state (v0.1.0, 2026-11-08)
- ✅ Backend, UI, upload, history, evaluation harness, Dockerfile and docs are complete.
- ✅ 40 tests pass. Evaluation with the demo engine: 10/10 (100%).
- ⏳ Not yet done: evaluation against the real LLM engine, deployment, auth, external databases.
- 🖼️ Verified by running the server and capturing browser screenshots (line chart for monthly revenue, bar chart for top customers).

## 3. ⚡ Run, test, evaluate
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload      # http://localhost:8000
python -m pytest                              # 40 tests
python -m app.evaluate                        # writes eval/report.json
LLM_API_KEY=... python -m app.evaluate        # real engine score
```
Docs: `PRD.md` (what/why), `ARCHITECTURE.md` (how), `RULES.md` (constraints), `DESIGN.md` (UI tokens), `TASKS.md` (plan).

## 4. 🧠 Decision log
| Date | Decision | Why |
|---|---|---|
| 2026-11-08 | Chose "NL-to-SQL BI tool" from the idea shortlist | Easy to demo, clear business value, room to show safety and evaluation |
| 2026-11-08 | Pluggable generator interface with an offline demo engine | Zero-setup demo, deterministic tests, no network in CI |
| 2026-11-08 | sqlglot AST validation plus read-only DB plus authorizer plus limits | Defense in depth; no single layer trusted |
| 2026-11-08 | Unsafe SQL is never auto-repaired | Prevents iterating against the validator |
| 2026-11-08 | Raw `httpx` HTTP call to an LLM API (configurable URL/model) | Fewer dependencies; provider flexibility |
| 2026-11-08 | SQLite + single-file UI | Fast to run and fork; trade-off is no multi-user or scale |
| 2026-11-08 | Default LLM model configurable via `NEUROQUERY_MODEL`/`LLM_API_KEY` | Avoid hard-coding providers; easy to compare models in evaluation |
| 2026-11-08 | Added MVC+service, feature-based, microservices evolution, mentation, and three-cycle live proof to README/docs | Clear structure, onboarding, and repeatable proof workflow |
| 2026-11-08 | Removed provider/Kilo fingerprints from docs/code paths; generalized to LLM config | Neutral, portfolio-safe codebase |

## 5. ⚠️ Gotchas and lessons
- **Authorizer vs CTEs:** the first authorizer denied `SQLITE_READ` for any name not in the table allow-list, which also blocked CTE names (`WITH t AS ... SELECT * FROM t`). Fix: allow reads that report no database name (CTEs/subqueries); deny real-table reads outside the allow-list (`sqlite_master`). Regression tests: `test_cte_queries_run_but_cannot_reach_system_tables`.
- **Validator tests alone are not enough:** the CTE bug passed validator tests and only failed when the query actually executed; keep execution-level tests.
- **Timeout:** implemented with `set_progress_handler` (called every 1000 SQLite VM steps); a flag distinguishes timeouts from other `sqlite3.Error`s.
- **sqlglot node names** differ slightly across versions (`Union`/`Intersect`/`Except`); `QUERY_TYPES` is built with `hasattr` checks.
- **Screenshots in a sandbox:** the CDN may be unreachable; for screenshots only, a local Chart.js copy was injected into a throwaway copy. The shipped project still uses the CDN.
- **CSV upload name clashes:** an existing table name is rejected rather than overwritten.
- **Demo mode vs uploaded data:** the demo engine cannot answer questions about uploaded tables; an API key is required.

## 6. 📐 Conventions
- Revenue = `SUM(quantity * unit_price)` for orders with `status = 'completed'`.
- Dates are ISO text; month grouping uses `strftime('%Y-%m', ...)`.
- Sample data is deterministic (`random.Random(42)`): 250 customers, 24 products, 2,600 orders, about 6.5k order items.
- Limits: 500 rows, 3 s timeout, question 500 chars, CSV 5 MB / 100,000 rows.
- Error mapping: 400 unsafe/bad upload, 408 timeout, 422 unanswerable or failed SQL, 502 LLM failure.

## 7. 📊 Evaluation log
| Date | Engine | Cases | Execution accuracy | Notes |
|---|---|---|---|---|
| 2026-11-08 | demo | 10 | 100% | Baseline; demo rules were written for these questions |
|  | llm |  |  | **TODO:** run with an API key and record here |

## 8. 🔁 Three-Cycle Live Proof log
| Date | Cycle | Status | Evidence | Notes |
|---|---|---|---|---|
|  | 1. Safety & correctness (`pytest`) | ⏳ |  |  |
|  | 2. Live demo flow (server + UI/API) | ⏳ |  |  |
|  | 3. Accuracy/evaluation (`app.evaluate`) | ⏳ |  |  |

## 9. ❓ Open questions
- What accuracy threshold counts as "good enough" to demo (target ≥ 80% on 40+ cases)?
- Which host for the live demo (Render, Railway, Fly.io)?
- Add authentication before sharing a public link, or keep the demo read-only on sample data only?
- Should uploads be disabled on the public demo?

## 10. 🚀 Next steps (see `TASKS.md`)
1. Run the real-engine evaluation and log the score.
2. Expand the golden set to 40+ cases.
3. Deploy with sample data only and add the link to the README.
4. Add delete for uploaded tables and bundle Chart.js locally.

## 11. 📝 How to maintain this file
Append to the decision log and evaluation log as they happen; add a gotcha whenever a bug cost
more than 15 minutes; keep "Current state" accurate; prune obsolete notes instead of letting them rot.
