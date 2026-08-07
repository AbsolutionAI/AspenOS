"""ASP-77 — Paperclip memory ingestion hook tests.

Verifies ``agents/paperclip_memory.py::ingest_paperclip_record`` writes BEL-154
raw ingest records (source="paperclip") that the promotion pipeline
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

import paperclip_memory as pm  # noqa: E402
import memory_promote as mp  # noqa: E402


def _records(ingest_dir):
    return list(mp._iter_ingest_records(ingest_dir, None))


class TestIngestPaperclipRecord:
    def test_writes_paperclip_record_to_daily_file(self, tmp_path):
        pm.ingest_paperclip_record(
            "Implemented the Paperclip ingestion hook.",
            source_id="ASP-77",
            files=["agents/paperclip_memory.py"],
            tools=["bash", "edit", "read"],
            linear_refs=["BEL-154"],
            paperclip_refs=["ASP-77"],
            ingest_dir=tmp_path,
        )
        records = _records(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["source"] == "paperclip"
        assert rec["agent"] == "paperclip"
        assert rec["company"] == "asp"
        assert rec["project"] == "aspen-os"
        assert rec["source_id"] == "ASP-77"
        assert rec["content"] == "Implemented the Paperclip ingestion hook."
        assert rec["metadata"]["files_touched"] == ["agents/paperclip_memory.py"]
        assert rec["metadata"]["tools_used"] == ["bash", "edit", "read"]
        assert rec["metadata"]["linear_refs"] == ["BEL-154"]
        assert rec["metadata"]["paperclip_refs"] == ["ASP-77"]

    def test_source_id_falls_back_to_agent_timestamp(self, tmp_path):
        pm.ingest_paperclip_record("hello", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        assert rec["source_id"].startswith("paperclip:")

    def test_empty_content_still_schema_valid(self, tmp_path):
        pm.ingest_paperclip_record("", source_id="ASP-77", ingest_dir=tmp_path)
        (rec,) = _records(tmp_path)
        json.dumps(rec)  # serializable
        assert rec["source"] == "paperclip"
        assert rec["content"] == ""

    def test_content_truncated_to_max_content_chars(self, tmp_path):
        long_content = "x" * 5000
        pm.ingest_paperclip_record(
            long_content, source_id="ASP-77", ingest_dir=tmp_path,
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
        result = pm.ingest_paperclip_record(
            "boom", source_id="ASP-77", ingest_dir=tmp_path,
        )  # must not raise
        assert result is None


class TestPaperclipMemoryCLI:
    def test_cli_writes_from_content_arg(self, tmp_path, capsys):
        rc = pm.main([
            "--source-id", "ASP-77",
            "--content", "CLI summary",
            "--files", "agents/paperclip_memory.py, docs/plans",
            "--tools", "bash, edit",
            "--ingest-dir", str(tmp_path),
        ])
        assert rc == 0
        (rec,) = _records(tmp_path)
        assert rec["source"] == "paperclip"
        assert rec["content"] == "CLI summary"
        assert rec["metadata"]["files_touched"] == [
            "agents/paperclip_memory.py", "docs/plans",
        ]
        out = capsys.readouterr().out.strip()
        assert str(tmp_path) in out  # prints written path

    def test_cli_writes_from_stdin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda s: "stdin body"})())
        rc = pm.main(["--source-id", "ASP-77", "--stdin",
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
        rc = pm.main(["--source-id", "ASP-77", "--content", "x",
                      "--ingest-dir", str(tmp_path)])
        assert rc == 2

    def test_cli_no_ingest_dir_uses_default(self, monkeypatch):
        """Regression guard: passing ingest_dir=None must not crash the CLI
        (the ASP-61 ingest_dir=None bug)."""
        from scripts.memory_ingest import DEFAULT_INGEST_DIR
        default = DEFAULT_INGEST_DIR / "paperclip"
        if default.exists():
            monkeypatch.delenv("AGNETIC_MEMORY_INGEST_DIR", raising=False)
        import scripts.memory_ingest as mi

        real_ingest = mi.ingest_record
        written = {}

        def fake_ingest(source, source_id, content, **kw):
            written["ingest_dir"] = kw.get("ingest_dir")
            return real_ingest(source, source_id, content, **kw)

        monkeypatch.setattr(mi, "ingest_record", fake_ingest)
        rc = pm.main(["--source-id", "ASP-77", "--content", "x"])
        assert rc == 0
        assert written["ingest_dir"] is not None
