# 📏 RULES: NEUROQUERY

Rules for contributors and AI coding assistants working in this repository.

## 1. 🛡️ Non-negotiable safety rules
1. **Generated SQL is untrusted input.** Always run it through `validate_sql()` before execution, in every code path (API, evaluation, scripts).
2. Execute queries only through `Database.run_query()`. Never open a writable connection for user or model SQL.
3. Never weaken or remove a safety layer (validator, read-only mode, authorizer, row cap, timeout) to make a feature or test pass.
4. **Never auto-repair unsafe SQL.** Only `QueryError` (execution failures) may trigger `repair()`, and at most once.
5. Keep the table allow-list authoritative: `db.table_names()` only, never model-supplied names.
6. Never log, store, echo or commit API keys. Read them from environment variables only.
7. Only `import_csv()` may write to the data database, and it must sanitize table and column names and quote identifiers.
8. Any change to safety code requires new adversarial tests in `tests/test_safety.py` and/or `tests/test_db.py`.

## 2. 💻 Code rules
- Python 3.10+, type hints on public functions, `from __future__ import annotations`.
- Keep modules single-purpose as listed in `docs/ARCHITECTURE.md`; do not mix HTTP code into `db.py`, `safety.py` or `llm.py`.
- New generators implement `generate(question, schema_text)` and `repair(question, schema_text, bad_sql, error)` and expose a `name`.
- Raise typed exceptions (`UnsafeSQLError`, `QueryError`, `QueryTimeout`, `NoAnswer`, `GenerationError`, `CSVImportError`) and map them to HTTP codes only in `main.py`.
- Error messages shown to users must be actionable and must not leak stack traces, file paths or keys.
- Use parameterized SQL for app-owned queries; quote identifiers for dynamic names.
- Keep dependencies minimal; justify any new one in `docs/MEMORY.md`.
- No global mutable state; build everything inside `create_app()`.

## 3. ✅ Testing rules
- Every new endpoint, rule or safety behavior ships with tests. The suite must pass: `python -m pytest`.
- Tests must not need network access or API keys; inject a fake generator instead.
- Use `tmp_path` data directories; never write into the repository `data/` folder from tests.
- Adding a demo rule requires a matching case in `eval/golden.json`.
- Run `python -m app.evaluate` before and after changes to prompts, schema text or generators, and record notable score changes in `docs/MEMORY.md`.

## 4. 🤖 LLM and prompt rules
- The system prompt requires a JSON-only reply with a single read-only SELECT; keep that contract and parse defensively.
- Schema text must come from the live database (`schema_text()`), not hard-coded strings; business notes live in `db.BUSINESS_NOTES`.
- Model name is configurable (`NEUROQUERY_MODEL`); do not hard-code it elsewhere.
- Treat model explanations as display text only; never execute or trust them.

## 5. 🔌 API and data rules
- Preserve response field names (`sql`, `explanation`, `columns`, `rows`, `chart`, ...); additive changes only unless the UI and tests are updated together.
- Keep limits configurable via environment: rows, timeout. Uploads stay capped (5 MB, 100,000 rows).
- Database files live under `NEUROQUERY_DATA_DIR`; `data/` stays git-ignored.
- The sample dataset is deterministic (seed 42); changing it requires updating counts in tests and docs.

## 6. 🎨 UI rules
- Follow `docs/DESIGN.md` tokens; no hard-coded colors outside the `:root` variables and the chart palette.
- Escape all dynamic text (`esc()` or `textContent`); never insert model or data values with raw `innerHTML`.
- The UI must work without the chart library (table still renders) and remain usable at 380 px wide.

## 7. 🔁 Workflow rules
- Small, focused commits with imperative messages (for example `Add CSV delete endpoint`).
- Update `docs/TASKS.md` when starting or finishing work, and `docs/MEMORY.md` when making a decision or learning a gotcha.
- Do not make unrequested changes outside the scope of the task.
- No secrets, databases or `eval/report.json` in version control.
- **Three-Cycle Live Proof** for meaningful changes: (1) `pytest`/safety, (2) live demo flow, (3) evaluation — record outcomes in `docs/MEMORY.md`.

## 8. 🏁 Definition of done
- [ ] ✅ Tests added or updated and passing
- [ ] 🛡️ Safety rules above still hold
- [ ] 📊 `python -m app.evaluate` run if the engine, prompt or schema text changed
- [ ] 📝 Docs updated (`TASKS.md`, `MEMORY.md`, plus `ARCHITECTURE.md` if structure or API changed)
- [ ] 🧪 Works in demo mode with no API key
