# 📋 PRD: NEUROQUERY

**Status:** MVP built (v0.1.0) · **Type:** AI / Data Science portfolio project

## 1. 🧾 Summary
NEUROQUERY lets a non-technical user ask questions about a database in plain English and get back
the generated SQL, a result table and an automatically chosen chart. The MVP focuses on
trustworthy answers: every query passes layered safety checks and the engine is measurable
with an evaluation harness.

## 2. ❗ Problem
- Business users depend on analysts for simple questions ("revenue by month?"), creating delays.
- Raw LLM-to-SQL demos are unsafe (writes, data leaks, runaway queries) and unmeasured (no accuracy numbers).

## 3. 🎯 Goals
1. 💬 Answer natural-language questions with SQL, table and chart in one screen.
2. 🛡️ Make execution **safe by construction**: read-only, allow-listed tables, bounded cost.
3. 📊 Be **measurable**: execution-accuracy score on a golden question set.
4. ⚡ Work with **zero setup** (offline demo mode) and **real NL** with one API key.
5. 📤 Let users bring their own data (CSV upload).

## 4. 🚫 Non-goals (MVP)
- Multi-user accounts, permissions, or tenant isolation.
- External databases (Postgres, MySQL, warehouses).
- Dashboards, scheduling, alerts, sharing.
- Write operations of any kind.
- Streaming responses and multi-turn conversational context.

## 5. 👥 Target users
| Persona | Need |
|---|---|
| Business user / manager | Quick answers without writing SQL |
| Junior analyst | Starting-point SQL they can read and learn from |
| Recruiter / interviewer (portfolio audience) | Clear evidence of AI engineering, safety thinking and evaluation |

## 6. 🧑‍💻 User stories
- 💬 As a user, I type a question and see the SQL, rows and a chart.
- 💡 As a user, I can click example questions to learn what is possible.
- 📤 As a user, I can upload a CSV and ask questions about it.
- 🕘 As a user, I can re-run a past question from history.
- 📋 As a user, I can copy the SQL and download results as CSV.
- ⚠️ As a user, I get a clear error when a question cannot be answered or SQL is blocked.
- 📊 As a maintainer, I can run an evaluation to see how accurate the engine is.

## 7. ⚙️ Functional requirements
| ID | Requirement | Status |
|---|---|---|
| F1 | `POST /api/ask` returns sql, explanation, columns, rows, chart suggestion, timing | ✅ Done |
| F2 | Schema-aware prompting (tables, columns, FKs, low-cardinality values, business notes) | ✅ Done |
| F3 | One automatic repair retry when generated SQL fails to execute | ✅ Done |
| F4 | Chart selection: metric / line (time series) / bar (≤25 categories) / table | ✅ Done |
| F5 | CSV upload with type inference becomes a queryable table | ✅ Done |
| F6 | Query history (latest N, persisted) | ✅ Done |
| F7 | Offline demo engine for sample database | ✅ Done |
| F8 | Execution-accuracy evaluation CLI + golden set | ✅ Done |
| F9 | Copy SQL, download result CSV | ✅ Done |
| F10 | Light and dark theme following system setting | ✅ Done |

## 8. 🛡️ Safety requirements
| ID | Requirement |
|---|---|
| S1 | Only a single SELECT/WITH/UNION statement is executed |
| S2 | Only known tables are readable; system tables are blocked |
| S3 | DB connection is read-only; an authorizer permits only SELECT and allow-listed reads |
| S4 | Row cap (default 500, reported as truncated) and timeout (default 3 s) |
| S5 | Unsafe SQL is rejected (HTTP 400) and never auto-repaired |
| S6 | API keys are read from environment, never stored or logged |

## 9. 📏 Success metrics
- 📊 Execution accuracy on golden set: demo engine 100% (baseline); target ≥ 80% with the LLM engine on an expanded set.
- ⚡ Median response time for demo queries under 100 ms; LLM queries dominated by model latency.
- 🛡️ 0 successful write / system-table access in adversarial tests (currently covered by the test suite).
- ✅ Test suite green: 40 tests.

## 10. 🧱 Constraints and assumptions
- SQLite only; single shared database per deployment.
- LLM mode needs `LLM_API_KEY` (and optional `LLM_API_URL`/`NEUROQUERY_MODEL`) and outbound network access.
- Browser needs internet to load Chart.js from the CDN (table view works without).

## 11. ⚠️ Risks
| Risk | Mitigation |
|---|---|
| Model writes wrong-but-valid SQL | Show the SQL, evaluation harness, one-shot repair |
| Prompt injection via question or data | Validator + read-only DB + authorizer; never trust model output |
| Expensive queries | Timeout via progress handler, row cap |
| Sensitive uploaded data | No auth in MVP; run locally or add auth before exposing publicly |

## 12. 🔁 Three-Cycle Live Proof (spec)
1. **Cycle 1 — Safety & correctness:** `pytest` green; adversarial/safety coverage holds.
2. **Cycle 2 — Live demo flow:** run server, ask sample questions (+ optional upload), verify SQL/table/chart/history.
3. **Cycle 3 — Accuracy/evaluation:** run `app.evaluate` (demo + real), record score/deltas in `MEMORY.md`.

## 13. 🗺️ Future scope
Postgres/MySQL connectors with read-only roles, auth and per-user data, saved dashboards,
scheduled reports, few-shot learning from history, streaming and follow-up questions, cloud deploy.
