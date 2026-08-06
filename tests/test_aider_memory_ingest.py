"""ASP-61 — Aider memory ingestion hook tests.

Verifies ``agents/aider_memory.py::ingest_aider_record`` writes BEL-154 raw
ingest records (source="aider") that the promotion pipeline
(``memory_promote._iter_ingest_records``) can read back, that metadata and
truncation behave, that the CLI works from args and stdin, and that the hook is
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

import aider_memory as am  # noqa: E402
import memory_promote as mp  # noqa: E402


def _records(ingest_dir):
    return list(mp._iter_ingest_records(ingest_dir, None))


class TestIngestAiderRecord:
    def test_writes_aider_record_to_daily_file(self, tmp_path):
        am.ingest_aider_record(
            "Implemented the Aider ingestion hook.",
            source_id="ASP-61",
            files=["agents/aider_memory.py"],
            tools=["bash", "edit", "read"],
            linear_refs=["BEL-154"],
            paperclip_refs=["ASP-61"],
            ingest_dir=tmp_path,
        )
        records = _records(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["source"] == "aider"
        assert rec["agent"] == "aider"
        assert rec["company"] == "asp"
        assert rec["project"] == "aspen-os"
        assert rec["source_id"] == "ASP-61"
        assert rec["content"] == "Implemented the Aider ingestion hook."
        assert rec["metadata"]["files_touched"] == ["agents/aider_memory.py"]
        assert rec["metadata"]["tools_used"] == ["bash", "edit", "read"]
        assert rec["metadata"]["linear_refs"] == ["BEL-154"]
        assert rec["metadata"]["paperclip_refs"] == ["ASP-61"]

    def test_source_id_falls_back_to_agent_timestamp(self, tmp_path):
        am.ingest_aider_record("hello", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        assert rec["source_id"].startswith("aider:")

    def test_empty_content_still_schema_valid(self, tmp_path):
        am.ingest_aider_record("", source_id="ASP-61", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        json.dumps(rec)  # serializable
        assert rec["source"] == "aider"
        assert rec["content"] == ""

    def test_content_truncated_to_max_content_chars(self, tmp_path):
        long_content = "x" * 5000
        am.ingest_aider_record(
            long_content, source_id="ASP-61", ingest_dir=tmp_path,
            max_content_chars=1000,
        )
        (rec,) = _records(tmp_path)
        assert len(rec["content"]) == 1000

    def test_failure_is_isolated_never_raises(self, tmp_path, monkeypatch):
        real_import = builtins.__import__

        def broken_import(name, *args, **kwargs):
            if name == "scripts.memory_ingest":
                raise ImportError("no scripts on path")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", broken_import)
        result = am.ingest_aider_record(
            "boom", source_id="ASP-61", ingest_dir=tmp_path,
        )  # must not raise
        assert result is None


class TestAiderMemoryCLI:
    def test_cli_writes_from_content_arg(self, tmp_path, capsys):
        rc = am.main([
            "--source-id", "ASP-61",
            "--content", "CLI summary",
            "--files", "agents/aider_memory.py, docs/plans",
            "--tools", "bash, edit",
            "--ingest-dir", str(tmp_path),
        ])
        assert rc == 0
        (rec,) = _records(tmp_path)
        assert rec["source"] == "aider"
        assert rec["content"] == "CLI summary"
        assert rec["metadata"]["files_touched"] == [
            "agents/aider_memory.py", "docs/plans",
        ]
        out = capsys.readouterr().out.strip()
        assert str(tmp_path) in out  # prints written path

    def test_cli_writes_from_stdin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda s: "stdin body"})())
        rc = am.main(["--source-id", "ASP-61", "--stdin",
                      "--ingest-dir", str(tmp_path)])
        assert rc == 0
        (rec,) = _records(tmp_path)
        assert rec["content"] == "stdin body"

    def test_cli_errors_return_2(self, tmp_path, monkeypatch):
        real_import = builtins.__import__

        def broken_import(name, *args, **kwargs):
            if name == "scripts.memory_ingest":
                raise ImportError("no scripts on path")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", broken_import)
        rc = am.main(["--source-id", "ASP-61", "--content", "x",
                      "--ingest-dir", str(tmp_path)])
        assert rc == 2
