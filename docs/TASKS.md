# ✅ TASKS: NEUROQUERY

Legend: `[x]` done · `[ ]` to do · priority P0 (next) / P1 / P2.

## 🔁 Three-Cycle Live Proof (active spec)
- [ ] **P0** **Cycle 1 — Safety & correctness:** run `python -m pytest`; confirm 0 failures and safety rules intact.
- [ ] **P0** **Cycle 2 — Live demo flow:** run server, ask 2–3 sample questions (+ optional CSV upload), verify SQL/table/chart/history and clear errors.
- [ ] **P0** **Cycle 3 — Accuracy/evaluation:** run demo + real `python -m app.evaluate`; record scores/deltas in `docs/MEMORY.md`; expand/review `eval/golden.json` as needed.

## 🏁 MVP (v0.1.0): complete
### 🧩 Backend
- [x] FastAPI app factory with `/api/ask`, `/schema`, `/examples`, `/history`, `/upload`, `/health`
- [x] Deterministic sample e-commerce database (seeded on first start)
- [x] Schema introspection and prompt-ready `schema_text()` (FKs, low-cardinality values, business notes)
- [x] Pluggable generators: Anthropic (Messages API via httpx) and offline Demo
- [x] One-shot SQL self-repair on execution errors
- [x] CSV upload with type inference and size/row limits
- [x] Persistent query history

### 🛡️ Safety
- [x] sqlglot AST validator (single SELECT, allow-listed tables, blocked functions and statements)
- [x] Read-only SQLite connection
- [x] SQLite authorizer (fixed bug: CTE reads were wrongly denied)
- [x] Row cap with truncation flag; query timeout
- [x] Adversarial tests for the above

### 🖥️ Frontend
- [x] Single-page UI: ask box, example chips, SQL view, chart, table
- [x] Chart selection: metric / line / bar / table
- [x] Copy SQL, download CSV, history re-run, CSV upload
- [x] Light and dark themes

### ✅ Quality and delivery
- [x] 40 automated tests (safety, DB, API, evaluation harness)
- [x] Evaluation harness and 10-case golden set (demo engine: 100%)
- [x] Dockerfile, README, `.env.example`, sample CSV
- [x] Project docs (PRD, ARCHITECTURE, RULES, DESIGN, TASKS, MEMORY)

## 🚀 Next (v0.2)
- [ ] **P0** Run the evaluation with the Claude engine and record the score in `MEMORY.md`
- [ ] **P0** Grow the golden set to 40+ questions (joins, filters, date ranges, ties, ambiguous wording)
- [ ] **P0** Deploy (Render, Railway or Fly.io) and add a live demo link to the README
- [ ] **P1** Delete uploaded tables from the UI (`DELETE /api/tables/{name}`, only for uploaded ones)
- [ ] **P1** Few-shot examples pulled from successful history to improve accuracy
- [ ] **P1** Show confidence or "assumptions" note when the model reports ambiguity
- [ ] **P1** Bundle Chart.js locally so the UI works offline
- [ ] **P1** Focus rings and aria-live regions (see `DESIGN.md` section 8)
- [ ] **P2** Follow-up questions with conversation context
- [ ] **P2** Streaming responses
- [ ] **P2** Column sorting and a chart-type switcher

## 🗺️ Later (v0.3+)
- [ ] 🔐 Authentication and per-user data and history
- [ ] 🔌 Postgres/MySQL connectors using read-only database roles
- [ ] 📊 Saved dashboards, scheduled reports, shareable links
- [ ] 💰 Query cost estimation (EXPLAIN) before running
- [ ] 📈 Per-schema evaluation sets and an accuracy dashboard
- [ ] 🤖 CI pipeline (tests + evaluation on every push)

## ⚠️ Known issues
- 📤 Uploaded tables cannot be removed from the UI (delete `data/neuroquery.db` to reset).
- 🧪 Demo engine only understands the sample questions.
- 🌐 Chart.js loads from a CDN, so charts need internet in the browser.
- 🕘 History is global (no user separation).

## 📝 How to use this file
Move items between sections as work starts and finishes; add the date and a one-line note in
`docs/MEMORY.md` for any decision or surprise.
