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
    MemoryStore = hi.load_memory_store()
    if MemoryStore is None:
        pytest.skip("holographic read-back NOT verified")

    # Read back through the store's real API. MemoryStore has no search_facts(); the
    # available read path is list_facts(). Match on the source_id, which _compose_fact
    # writes into the provenance header verbatim and which is unique to this record --
    # so this is a real round-trip check, not a substring match against prose.
    # (The previous needle, "OpenCode holographic", is not a substring of the stored
    # content: the header puts "ASP-HOLO-1" between the two words.)
    store = MemoryStore(db_path=str(db))
    facts = store.list_facts()
    assert facts, f"holographic store empty after dual-write: {db}"
    assert any("ASP-HOLO-1" in f["content"] for f in facts), [
        f["content"] for f in facts
    ]


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


def _broken_catalog(tmp_path):
    d = tmp_path / "plugins" / "holographic"
    d.mkdir(parents=True)
    (d / "holographic.py").write_text("import hermes_state_wal_does_not_exist  # broken\n")
    (d / "text.py").write_text("")
    (d / "store.py").write_text("class MemoryStore:\n    pass\n")
    return d


def test_broken_catalog_plugin_hard_fails_on_repeat(tmp_path, monkeypatch):
    """ASP-782 / PR #79: present-but-broken plugin must fail every call, never skip."""
    d = _broken_catalog(tmp_path)
    monkeypatch.setenv("ASPEN_HOLOGRAPHIC_PLUGIN", str(d))
    monkeypatch.setenv("ASPEN_HOLOGRAPHIC_DB", str(tmp_path / "holo.db"))
    monkeypatch.setattr(hi, "_MODULE_CACHE", {})
    # Ingest write swallows the failure first (isolation) ...
    assert hi.write_holographic(
        "Decision: broken plugin path.", source="opencode", source_id="X1"
    ) is None
    # ... but later loader calls must still raise, not return None.
    for _ in range(2):
        with pytest.raises(ModuleNotFoundError):
            hi.load_memory_store()


def test_absent_catalog_plugin_returns_none(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ASPEN_HOLOGRAPHIC_PLUGIN", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(hi, "_MODULE_CACHE", {})
    assert hi.load_memory_store() is None
    assert hi.load_memory_store() is None
    assert "holographic read-back NOT verified" in capsys.readouterr().err
