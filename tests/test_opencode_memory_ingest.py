"""ASP-60 — OpenCode memory ingestion hook tests.

Verifies ``agents/opencode_memory.py::ingest_opencode_record`` writes BEL-154
raw ingest records (source="opencode") that the promotion pipeline
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

import opencode_memory as om  # noqa: E402
import memory_promote as mp  # noqa: E402


def _records(ingest_dir):
    return list(mp._iter_ingest_records(ingest_dir, None))


class TestIngestOpencodeRecord:
    def test_writes_opencode_record_to_daily_file(self, tmp_path):
        om.ingest_opencode_record(
            "Implemented the OpenCode ingestion hook.",
            source_id="ASP-60",
            files=["agents/opencode_memory.py"],
            tools=["bash", "edit", "read"],
            linear_refs=["BEL-154"],
            paperclip_refs=["ASP-60"],
            ingest_dir=tmp_path,
        )
        records = _records(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["source"] == "opencode"
        assert rec["agent"] == "opencode"
        assert rec["company"] == "asp"
        assert rec["project"] == "aspen-os"
        assert rec["source_id"] == "ASP-60"
        assert rec["content"] == "Implemented the OpenCode ingestion hook."
        assert rec["metadata"]["files_touched"] == ["agents/opencode_memory.py"]
        assert rec["metadata"]["tools_used"] == ["bash", "edit", "read"]
        assert rec["metadata"]["linear_refs"] == ["BEL-154"]
        assert rec["metadata"]["paperclip_refs"] == ["ASP-60"]

    def test_source_id_falls_back_to_agent_timestamp(self, tmp_path):
        om.ingest_opencode_record("hello", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        assert rec["source_id"].startswith("opencode:")

    def test_empty_content_still_schema_valid(self, tmp_path):
        om.ingest_opencode_record("", source_id="ASP-60", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        json.dumps(rec)  # serializable
        assert rec["source"] == "opencode"
        assert rec["content"] == ""

    def test_content_truncated_to_max_content_chars(self, tmp_path):
        long_content = "x" * 5000
        om.ingest_opencode_record(
            long_content, source_id="ASP-60", ingest_dir=tmp_path,
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
        result = om.ingest_opencode_record(
            "boom", source_id="ASP-60", ingest_dir=tmp_path,
        )  # must not raise
        assert result is None


class TestOpencodeMemoryCLI:
    def test_cli_writes_from_content_arg(self, tmp_path, capsys):
        rc = om.main([
            "--source-id", "ASP-60",
            "--content", "CLI summary",
            "--files", "agents/opencode_memory.py, docs/plans",
            "--tools", "bash, edit",
            "--ingest-dir", str(tmp_path),
        ])
        assert rc == 0
        (rec,) = _records(tmp_path)
        assert rec["source"] == "opencode"
        assert rec["content"] == "CLI summary"
        assert rec["metadata"]["files_touched"] == [
            "agents/opencode_memory.py", "docs/plans",
        ]
        out = capsys.readouterr().out.strip()
        assert str(tmp_path) in out  # prints written path

    def test_cli_writes_from_stdin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda s: "stdin body"})())
        rc = om.main(["--source-id", "ASP-60", "--stdin",
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
        rc = om.main(["--source-id", "ASP-60", "--content", "x",
                      "--ingest-dir", str(tmp_path)])
        assert rc == 2
