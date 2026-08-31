"""Holographic dual-write from BEL-154 ingest (shared SQLite)."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "agents"))

import grokbuild_memory as gm
import holographic_ingest as hi
import memory_ingest as mi


def test_tmp_ingest_dir_does_not_touch_prod_db(tmp_path, monkeypatch):
    monkeypatch.delenv("ASPEN_HOLOGRAPHIC_DB", raising=False)
    monkeypatch.delenv("ASPEN_HOLOGRAPHIC_DISABLE", raising=False)
    assert hi._should_write(tmp_path, mi.DEFAULT_INGEST_DIR) is False
    mi.ingest_record("paperclip", "test-skip", "Decision: skip prod db.", ingest_dir=tmp_path)


def test_explicit_db_env_writes_holographic(tmp_path, monkeypatch):
    db = tmp_path / "holo.db"
    monkeypatch.setenv("ASPEN_HOLOGRAPHIC_DB", str(db))
    ingest = tmp_path / "ingest"
    path = mi.ingest_record(
        "opencode",
        "ASP-HOLO-1",
        "Decision: dual-write OpenCode ingest into holographic.",
        agent="opencode",
        project="aspen-os",
        linear_refs=["BEL-154"],
        paperclip_refs=["ASP-HOLO-1"],
        ingest_dir=ingest,
    )
    assert path.exists()
    sys.path.insert(0, "/home/tech/.hermes/hermes-agent")
    try:
        from plugins.memory.holographic.store import MemoryStore
    except ModuleNotFoundError as exc:
        if "tools.registry" in str(exc) or "holographic" in str(exc):
            pytest.skip("Hermes holographic plugin not available", allow_module_level=False)
        raise

    store = MemoryStore(db_path=str(db))
    hits = store.search_facts("OpenCode holographic")
    assert hits, hits


def test_grokbuild_source_accepted(tmp_path):
    path = mi.ingest_record(
        "grokbuild", "CHG-TEST", "Decision: Grok Build can ingest.",
        ingest_dir=tmp_path,
    )
    assert path.exists()
    rec = path.read_text()
    assert '"source": "grokbuild"' in rec


def test_grokbuild_hook_writes(tmp_path):
    gm.ingest_grokbuild_record(
        "Decision: Grok Build hook writes BEL-154 records.",
        source_id="GB-1",
        files=["agents/grokbuild_memory.py"],
        linear_refs=["BEL-154"],
        ingest_dir=tmp_path,
    )
    files = list((tmp_path / "grokbuild").glob("*.jsonl"))
    assert len(files) == 1
    assert "Grok Build hook" in files[0].read_text()


def test_all_four_writers_jsonl(tmp_path):
    import aider_memory as am
    import opencode_memory as om
    import paperclip_memory as pm

    pm.ingest_paperclip_record("Paperclip writer smoke.", source_id="P1", ingest_dir=tmp_path)
    om.ingest_opencode_record("OpenCode writer smoke.", source_id="O1", ingest_dir=tmp_path)
    am.ingest_aider_record("Aider writer smoke.", source_id="A1", ingest_dir=tmp_path)
    gm.ingest_grokbuild_record("Grok Build writer smoke.", source_id="G1", ingest_dir=tmp_path)
    for src in ("paperclip", "opencode", "aider", "grokbuild"):
        assert list((tmp_path / src).glob("*.jsonl"))
