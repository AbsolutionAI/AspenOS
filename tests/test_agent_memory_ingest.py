"""ASP-59 — Hermes daemon memory ingestion hook tests.

Verifies ``agents/agent_daemon.py::ingest_memory_record`` writes BEL-154-schema
raw ingest records (source="hermes") that the promotion pipeline
(``memory_promote._iter_ingest_records``) can read back, and that the hook is
failure-isolated (a broken import/write never raises).
"""

import builtins
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "services"))
sys.path.insert(0, str(PROJECT_ROOT / "agents"))

import agent_daemon as ad  # noqa: E402
import memory_promote as mp  # noqa: E402


def _records(ingest_dir):
    return list(mp._iter_ingest_records(ingest_dir, None))


class TestIngestMemoryRecord:
    def test_writes_hermes_record_to_daily_file(self, tmp_path):
        ad.ingest_memory_record(
            "proxy", "status check", {"format": "json"},
            "All systems nominal.", subject="starship.agent.proxy.command.status",
            ingest_dir=tmp_path,
        )
        records = _records(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["source"] == "hermes"
        assert rec["agent"] == "proxy"
        assert rec["company"] == "asp"
        assert rec["project"] == "aspen-os"
        assert rec["source_id"] == "starship.agent.proxy.command.status"
        assert "Command: status check" in rec["content"]
        assert "All systems nominal." in rec["content"]

    def test_source_id_falls_back_to_agent_timestamp(self, tmp_path):
        ad.ingest_memory_record("ergo", "hello", None, "hi", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        assert rec["source_id"].startswith("ergo:")

    def test_no_args_still_schema_valid(self, tmp_path):
        ad.ingest_memory_record("romi", "greet", None, "hola", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        json.dumps(rec)  # serializable
        assert rec["content"].startswith("Command: greet")
        assert "Response: hola" in rec["content"]

    def test_response_truncated_to_2000_chars(self, tmp_path):
        long_response = "x" * 5000
        ad.ingest_memory_record("proxy", "dump", {}, long_response, ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        assert len(rec["content"]) < 3000
        assert "x" * 2000 in rec["content"]

    def test_failure_is_isolated_never_raises(self, tmp_path, monkeypatch):
        real_import = builtins.__import__

        def broken_import(name, *args, **kwargs):
            if name == "scripts.memory_ingest":
                raise ImportError("no scripts on path")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", broken_import)
        ad.ingest_memory_record(
            "proxy", "boom", {}, "oops", ingest_dir=tmp_path,
        )  # must not raise
