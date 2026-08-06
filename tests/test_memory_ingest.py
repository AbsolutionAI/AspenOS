"""ASP-57 — BEL-154 ingestion layer tests.

Verifies ``scripts/memory_ingest.py`` writes BEL-154-schema JSONL records that
the promotion pipeline (``memory_promote._iter_ingest_records``) can read back.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

import memory_ingest as mi  # noqa: E402
import memory_promote as mp  # noqa: E402


class TestIngestRecord:
    def test_writes_schema_line_to_daily_file(self, tmp_path):
        path = mi.ingest_record(
            "paperclip", "run-123", "Decision: use DeepSeek V4-Flash.",
            ingest_dir=tmp_path,
            linear_refs=["BEL-154"],
            paperclip_refs=["ABS-10"],
        )
        assert path.exists()
        assert path.name == datetime.now(timezone.utc).strftime("%Y-%m-%d.jsonl")
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["source"] == "paperclip"
        assert record["source_id"] == "run-123"
        assert record["content"] == "Decision: use DeepSeek V4-Flash."
        assert record["metadata"]["linear_refs"] == ["BEL-154"]
        assert record["metadata"]["paperclip_refs"] == ["ABS-10"]

    def test_invalid_source_raises(self, tmp_path):
        with pytest.raises(ValueError):
            mi.ingest_record("spreadsheet", "x", "content", ingest_dir=tmp_path)

    def test_timestamp_defaults_to_now_utc(self, tmp_path):
        path = mi.ingest_record("opencode", "t-1", "content", ingest_dir=tmp_path)
        record = json.loads(path.read_text().splitlines()[0])
        assert record["timestamp"].endswith("Z")
        datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))

    def test_explicit_timestamp_and_metadata_lists(self, tmp_path):
        path = mi.ingest_record(
            "hermes", "sess-9", "content",
            agent="ergo", company="abs", project="aspen-os",
            tools=["terminal", "web_search"],
            files=["services/memory.py"],
            linear_refs=["BEL-153"],
            paperclip_refs=["ABS-7"],
            timestamp="2026-08-04T21:00:00Z",
            ingest_dir=tmp_path,
        )
        record = json.loads(path.read_text().splitlines()[0])
        assert record["agent"] == "ergo"
        assert record["company"] == "abs"
        assert record["project"] == "aspen-os"
        assert record["timestamp"] == "2026-08-04T21:00:00Z"
        assert record["metadata"]["tools_used"] == ["terminal", "web_search"]
        assert record["metadata"]["files_touched"] == ["services/memory.py"]

    def test_append_multiple_records_to_same_file(self, tmp_path):
        mi.ingest_record("aider", "c1", "first", ingest_dir=tmp_path)
        mi.ingest_record("aider", "c2", "second", ingest_dir=tmp_path)
        files = list((tmp_path / "aider").glob("*.jsonl"))
        assert len(files) == 1
        assert len(files[0].read_text().splitlines()) == 2

    def test_promote_pipeline_reads_written_file(self, tmp_path):
        mi.ingest_record(
            "paperclip", "run-1",
            "Decision: use SQLite json_each for metadata lookups.",
            agent="opencode",
            ingest_dir=tmp_path,
            linear_refs=["BEL-154"],
            paperclip_refs=["ABS-10"],
        )
        records = list(mp._iter_ingest_records(tmp_path, "paperclip"))
        assert len(records) == 1
        assert records[0]["source"] == "paperclip"
        assert records[0]["metadata"]["linear_refs"] == ["BEL-154"]


class TestCli:
    def test_main_returns_zero_and_creates_file(self, tmp_path):
        rc = mi.main([
            "--source", "opencode",
            "--source-id", "task-7",
            "--content", "Config: export AGNETIC_MEMORY_DB=/var/lib/memory.db",
            "--linear-refs", "BEL-154, BEL-153",
            "--ingest-dir", str(tmp_path),
        ])
        assert rc == 0
        written = list((tmp_path / "opencode").glob("*.jsonl"))
        assert len(written) == 1
        record = json.loads(written[0].read_text().splitlines()[0])
        assert record["metadata"]["linear_refs"] == ["BEL-154", "BEL-153"]

    def test_main_rejects_invalid_source(self, tmp_path, capsys):
        rc = mi.main([
            "--source", "nope",
            "--source-id", "x",
            "--content", "content",
            "--ingest-dir", str(tmp_path),
        ])
        assert rc == 2
        assert "invalid source" in capsys.readouterr().err
