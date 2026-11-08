import json

import pytest

from app.db import Database
from app.evaluate import GOLDEN_PATH, run_eval
from app.llm import DemoGenerator, GeneratedSQL


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "e.db")
    d.ensure_seeded()
    return d


def test_demo_engine_passes_golden_set(db):
    cases = json.loads(GOLDEN_PATH.read_text())
    report = run_eval(db, DemoGenerator(), cases)
    failed = [c for c in report["cases"] if not c["passed"]]
    assert not failed, failed
    assert report["execution_accuracy"] == 100.0


def test_harness_detects_wrong_answers(db):
    class Wrong:
        name = "wrong"

        def generate(self, q, schema):
            return GeneratedSQL("SELECT COUNT(*) FROM orders", "wrong on purpose")

    cases = json.loads(GOLDEN_PATH.read_text())
    report = run_eval(db, Wrong(), cases)
    assert report["passed"] < report["total"]
