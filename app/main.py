"""NEUROQUERY API: ask questions in plain English, get safe SQL, results and a chart."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .charts import suggest_chart
from .db import CSVImportError, Database, QueryError, QueryTimeout
from .history import History
from .llm import EXAMPLES, GenerationError, NoAnswer, get_generator
from .safety import UnsafeSQLError, validate_sql

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def create_app(data_dir: Path | str | None = None, generator=None) -> FastAPI:
    data_path = Path(data_dir or os.environ.get("NEUROQUERY_DATA_DIR") or ROOT / "data")
    data_path.mkdir(parents=True, exist_ok=True)
    max_rows = int(os.environ.get("NEUROQUERY_MAX_ROWS", "500"))
    timeout_s = float(os.environ.get("NEUROQUERY_QUERY_TIMEOUT", "3"))

    db = Database(data_path / "neuroquery.db")
    db.ensure_seeded()
    history = History(data_path / "history.db")
    gen = generator or get_generator()

    app = FastAPI(title="NEUROQUERY", version="0.1.0")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "engine": gen.name}

    @app.get("/api/schema")
    def schema():
        return {"tables": db.schema()}

    @app.get("/api/examples")
    def examples():
        return {"examples": EXAMPLES, "engine": gen.name}

    @app.get("/api/history")
    def get_history(limit: int = 20):
        return {"items": history.recent(max(1, min(limit, 100)))}

    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(400, "Please upload a .csv file.")
        data = await file.read()
        try:
            return db.import_csv(file.filename, data)
        except CSVImportError as e:
            raise HTTPException(400, str(e)) from e

    @app.post("/api/ask")
    def ask(req: AskRequest):
        question = req.question.strip()
        if len(question) < 3:
            raise HTTPException(422, "Please ask a longer question.")
        schema_text = db.schema_text()
        allowed = db.table_names()

        try:
            generated = gen.generate(question, schema_text)
        except NoAnswer as e:
            raise HTTPException(422, str(e)) from e
        except GenerationError as e:
            raise HTTPException(502, str(e)) from e

        attempts = 1
        while True:
            try:
                safe_sql = validate_sql(generated.sql, allowed)
                result = db.run_query(safe_sql, max_rows=max_rows, timeout_s=timeout_s)
                break
            except UnsafeSQLError as e:
                raise HTTPException(400, f"Blocked unsafe SQL: {e}") from e
            except QueryTimeout as e:
                raise HTTPException(408, f"Query timed out: {e}") from e
            except QueryError as e:
                if attempts >= 2:
                    raise HTTPException(422, f"The generated SQL failed to run: {e}") from e
                try:
                    generated = gen.repair(question, schema_text, generated.sql, str(e))
                except (NoAnswer, GenerationError) as e2:
                    raise HTTPException(422, f"The generated SQL failed to run: {e}") from e2
                attempts += 1

        history.add(question, safe_sql, result["row_count"], gen.name)
        return {
            "question": question,
            "sql": safe_sql,
            "explanation": generated.explanation,
            "engine": gen.name,
            "attempts": attempts,
            "chart": suggest_chart(result["columns"], result["rows"]),
            **result,
        }

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
