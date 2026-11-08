# 🧠 NEUROQUERY: ask your data in plain English

A natural-language-to-SQL BI tool. Type a question, get the generated SQL, a result table
and an auto-picked chart. Built as an AI/Data Science portfolio MVP with the parts most
student projects skip: **🛡️ SQL safety layers** and an **📊 evaluation harness**.

## 🚀 Quick start (no API key needed)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# open http://localhost:8000
```

Without a key the app runs in **🧪 offline demo mode**: a rule-based engine answers the sample
questions on the built-in e-commerce database (250 customers, 2,600 orders).

### 🤖 Real natural language (LLM)

```bash
export LLM_API_KEY=your_key      # Windows PowerShell: $env:LLM_API_KEY="your_key"
python -m uvicorn app.main:app --reload
```

Now any question works, including on your own data: use **📤 Upload CSV** in the sidebar
(try `sample_data/marketing_spend.csv`, then ask "total spend by channel").
Model is configurable with `NEUROQUERY_MODEL`. See `.env.example`.

## 🏗️ Architecture (current)

```
question -> schema-aware prompt -> LLM (or demo engine) -> SQL
         -> validator (sqlglot) -> read-only SQLite + authorizer + row cap + timeout
         -> result + chart suggestion -> UI (table, chart, CSV download, history)
                  ^                                  |
                  +---- one auto-repair retry <------+  (on SQL execution error)
```

| File | Role |
|---|---|
| `app/llm.py` | 🤖 `LLMGenerator` (real) and `DemoGenerator` (offline), same interface |
| `app/safety.py` | 🛡️ Static SQL validation: single SELECT only, table allow-list, blocked functions |
| `app/db.py` | 🗄️ Schema introspection, hardened read-only execution, CSV import |
| `app/charts.py` | 📈 Chooses metric / line / bar / table from result shape |
| `app/evaluate.py` | 📊 Execution-accuracy evaluation against `eval/golden.json` |
| `app/main.py` | 🌐 FastAPI endpoints and static UI hosting |

### 🛡️ Safety model (defense in depth)
1. 🔍 **Validator**: exactly one statement, SELECT/WITH/UNION only, known tables only, no
   `PRAGMA`/`ATTACH`/DDL/DML, no `load_extension`, no table-valued functions.
2. 🔒 **Read-only connection** (`mode=ro`), so writes are impossible at the database level.
3. 👮 **SQLite authorizer**: only `SELECT` plus reads on allow-listed tables; `sqlite_master` is blocked.
4. ⏱️ **Limits**: 500-row cap (flagged as truncated) and a 3 s query timeout.
5. 🚫 **No unsafe repair**: unsafe SQL is **never auto-repaired**; it is rejected with HTTP 400.

## 🔌 API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ask` | 💬 `{"question": "..."}` returns sql, rows, chart, explanation |
| GET | `/api/schema` | 🗂️ Tables, columns, row counts |
| GET | `/api/examples` | 💡 Example questions and active engine |
| GET | `/api/history` | 🕘 Recent questions |
| POST | `/api/upload` | 📤 Multipart CSV upload becomes a queryable table |
| GET | `/api/health` | ❤️ Status and engine name |

## 🧩 MVC + service structure

NEUROQUERY can be understood (and refactored) using an MVC + service layering. Today the layers are lightweight; the mapping below shows where responsibilities live and how to separate them as the codebase grows.

| Layer | Responsibility | Current mapping | Target (example) |
|---|---|---|---|
| **🗄️ Model** | Data shapes, schema, persistence contracts | `app/db.py` (schema/query), `app/history.py`, SQLite tables | `app/models/` (domain entities, DTOs/schemas) + repository interfaces |
| **🖥️ View** | Presentation / UI | `static/index.html` (table/chart rendering, CSV download) | `static/` or a frontend app (React/Vue) consuming the API |
| **🎛️ Controller** | HTTP boundary: parse input, call services, return responses | `app/main.py` (FastAPI routes) | Thin route handlers that delegate to services only |
| **⚙️ Service** | Business logic / orchestration (no HTTP, no UI) | Logic spread across `main.py`, `llm.py`, `safety.py`, `charts.py` | `app/services/` e.g. `query_service` (ask flow), `ingest_service` (CSV), `eval_service` |

**Key rules for this structure:**
- 🎛️ Controllers do **not** contain SQL, LLM, or chart logic—they orchestrate services.
- ⚙️ Services are **framework-agnostic** (testable without FastAPI/HTTP).
- 🗄️ Models/repositories own data access; services compose them with `safety`/`llm`/`charts`.

**Example flow (MVC + service):**
```
POST /api/ask (Controller) 
  -> QueryService.ask(question) 
       -> SchemaRepository.get_schema()        (Model/data)
       -> NL2SQLGenerator.generate(...)         (Service dependency)
       -> SQLValidator.validate(...)            (Service)
       -> QueryExecutor.run_readonly(...)       (Model/data)
       -> ChartSelector.suggest(...)            (Service)
  -> JSON response (View payload)
```

## 🧱 Feature-based structure

A feature-based (vertical-slice) layout groups code by capability instead of by technical layer. This scales better when features grow independently.

**Proposed layout:**
```
app/
  core/                     # shared infrastructure
    config.py               # env/config loading
    database.py             # connection, read-only execution, authorizer
    errors.py               # domain/HTTP error types
  features/
    ask/                    # NL -> SQL -> result
      router.py             # /api/ask endpoint(s)
      service.py            # orchestration: prompt, generate, validate, execute, repair
      schemas.py            # request/response models
      charts.py             # chart suggestion for this feature
    schema/
      router.py             # /api/schema
      service.py            # introspection
      schemas.py
    ingest/                 # CSV upload / data onboarding
      router.py             # /api/upload
      service.py            # import + table registration
    history/
      router.py             # /api/history
      repository.py         # persistence
    evaluation/
      harness.py            # execution-accuracy runner (or keep in eval/)
      golden.json
  integrations/
    llm/                    # LLM + demo engine adapters
      base.py               # generator interface
      provider.py
      demo.py
  safety/
    validator.py            # sqlglot/static validation rules
  main.py                   # app factory, mounts feature routers
static/
tests/
  features/
    ask/
    ingest/
    safety/
docs/
```

**Why feature-based here:** `ask` is the core slice (LLM + safety + DB + charting). Isolating it prevents `main.py` from becoming a god-module and makes it easy to add features like `auth`, `dashboards`, or `connectors` without cross-cutting edits.

## 🕸️ Microservices architecture (evolution path)

The current app is a **modular monolith**—the right starting point. Microservices make sense only when there are clear scaling/team boundaries (e.g., heavy LLM/eval workloads, independent data connectors, or multi-tenant isolation). Below is a pragmatic target.

| Service | Responsibility | Interface | Data/notes |
|---|---|---|---|
| **API Gateway / BFF** | Auth, rate limits, routing, aggregates responses for UI | HTTP to clients | Stateless |
| **Query Service** | NL2SQL orchestration: schema context, generation, validation, execution, chart suggestion | `POST /query` | Reads schema metadata; uses read-only DB access |
| **LLM Service** | Model/provider abstraction, prompt templates, retries/fallbacks, cost/latency telemetry | `POST /generate-sql` | Stateless; secrets isolated here |
| **Data Connector Service** | Schema introspection, read-only query execution, CSV/import, (future) Postgres/MySQL connectors | `POST /execute`, `GET /schema` | Owns DB credentials/policies; enforces row cap/timeout/authorizer |
| **Safety/Policy Service** *(optional split)* | Central SQL validation & policy decisions | `POST /validate` | Can be a library first; split if policies must be shared/audited independently |
| **Evaluation Service** *(async)* | Golden-set runs, regression scoring, failure reports | Jobs/queue + `GET /reports` | Runs offline/scheduled; stores results |
| **History/Audit Service** *(optional)* | Question/SQL/audit log persistence | Append/read API | PII-aware retention |

**Communication:** synchronous REST/gRPC between gateway and core services; async queue (e.g., Redis/SQS) for evaluation and heavy jobs. **Shared contract:** versioned schemas/DTOs; never share databases across services.

**Migration path (incremental):**
1. 🧱 **Modular monolith first** (now): clear module boundaries, service layer, interfaces for `Generator`/`Executor`/`Validator`.
2. 🧩 **Extract the safest seams:** move `LLM` behind an internal interface/adapter; keep safety + execution in-process until contracts are stable.
3. ✂️ **Split read-heavy/risky components:** isolate data connectors (credentials/policy) and/or evaluation (batch) as separate deployables.
4. ☁️ **Add platform concerns:** gateway auth, observability (traces/metrics), centralized config/secrets.

## 🧠 How to start (mentation / mental model)

Use this checklist to build the right mental model before changing code.

1. **🎯 Clarify the goal.** Is this a bug fix, a new feature, a safety change, or a refactor? For NEUROQUERY, any change that touches SQL generation/execution is **safety-critical**.
2. **🔎 Trace the end-to-end flow.** For a question: `UI -> POST /api/ask -> schema/prompt -> generator -> SQL -> safety.validate -> db.execute_readonly -> chart.suggest -> response`. Read `app/main.py` first, then follow into services/modules.
3. **🧩 Identify the layer/feature.** Decide: is it a controller concern (HTTP), service concern (orchestration), model/data concern (DB/schema), or integration concern (LLM)? Put logic in the right place (see MVC/feature sections).
4. **🛡️ Start with safety and contracts.** If SQL or data access changes, update/extend `app/safety.py` and its tests *before* trusting happy-path behavior. Keep the generator/DB behind interfaces.
5. **⚡ Run the fast feedback loop.**
   ```bash
   python -m pytest                 # correctness/safety
   python -m uvicorn app.main:app --reload
   python -m app.evaluate           # when NL2SQL behavior changes (with API key for real scoring)
   ```
6. **🪜 Make small vertical changes.** Prefer one feature slice at a time (route -> service -> data/integration -> tests). Avoid mixing refactors with behavior changes in the same step.
7. **📝 Document decisions.** Update `docs/` (and this README when architecture/structure changes) so the next change starts from an accurate model.

**Rule of thumb:** keep the **monolith modular** until you have a measured reason to distribute it (scaling, team ownership, compliance/isolation). Structure (MVC/service/feature) gives most of the benefits without distributed-system complexity.

## 🔁 Three-Cycle Live Proof (him-spec / mentation)

Use three tight cycles to prove NEUROQUERY works end-to-end (demo-safe, then real). Each cycle is: **Plan → Run → Verify → Record**.

| Cycle | Goal | What to run | Proof to capture | Exit criteria |
|---|---|---|---|---|
| **1) Safety & correctness** | Prove the pipeline is safe and green | `python -m pytest` | All tests pass (safety/DB/API/eval); no unsafe SQL path regressed | ✅ 0 failures; safety rules intact |
| **2) Live demo flow** | Prove the UI/API flow works | `python -m uvicorn app.main:app --reload` + ask 2–3 sample questions (and optional CSV upload) in `http://localhost:8000` | SQL shown, table/chart rendered, history updates; upload answers (with API key if needed) | ✅ End-to-end question answered; error states are clear |
| **3) Accuracy/evaluation** | Prove NL2SQL quality is measurable | `python -m app.evaluate` (demo) and `LLM_API_KEY=... python -m app.evaluate` (real) | `eval/report.json` + execution-accuracy score; note deltas/failures | ✅ Score recorded in `docs/MEMORY.md`; golden cases reviewed/expanded |

**Record after each cycle:** outcome, evidence (command/screenshot/report), and any decision/gotcha in `docs/MEMORY.md` / `docs/TASKS.md`.

## ✅ Tests and evaluation

```bash
python -m pytest                 # 40 tests: safety, DB hardening, API, eval harness
python -m app.evaluate           # execution accuracy on the golden question set
```

`eval/golden.json` holds question + reference SQL pairs. The harness runs both queries and
compares result sets (order-insensitive), which is the standard *execution accuracy* metric.
Run it with your API key to get a real score for the LLM, and add more cases as you find failures.

## 🐳 Docker

```bash
docker build -t neuroquery . && docker run -p 8000:8000 -e LLM_API_KEY=your_key neuroquery
```

## 🗺️ Roadmap (after the MVP)

- 🔌 Connect external databases (Postgres/MySQL) with a read-only role
- 👤 User accounts, saved dashboards, scheduled reports
- 🧠 Few-shot examples from history to improve accuracy; per-schema evaluation sets
- 🌊 Streaming responses, query explanations, follow-up questions with context
- ☁️ Deploy to Render/Railway/Fly.io with a live demo link

## 📄 Resume bullets

- 🤖 Built a natural-language-to-SQL analytics app (FastAPI, SQLite, LLM API) with schema-aware prompting, a one-shot SQL self-repair loop and automatic chart selection.
- 🛡️ Designed a 3-layer SQL safety model (sqlglot AST validation, read-only connection, SQLite authorizer) and verified it with adversarial tests.
- 📊 Implemented an execution-accuracy evaluation harness and a 40-test suite for regression tracking.

## 📚 Docs

| Doc | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product requirements (what/why) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design and request flow (how) |
| [`docs/RULES.md`](docs/RULES.md) | Safety, code, testing, and workflow rules |
| [`docs/DESIGN.md`](docs/DESIGN.md) | UI tokens and interaction states |
| [`docs/TASKS.md`](docs/TASKS.md) | Plan and three-cycle live proof checklist |
| [`docs/MEMORY.md`](docs/MEMORY.md) | Decisions, gotchas, evaluation/proof logs |
