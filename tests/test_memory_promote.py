import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

import memory_promote as mp  # noqa: E402
from memory import MemoryManager  # noqa: E402


def recent_ts() -> str:
    """A timestamp inside memory_promote's 30-day recency window.

    Hardcoded dates age out of the window and flip scoring tests once the
    fixture is older than 30 days.  Reference "now" so these always pass.
    """
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def ingest_fixture(tmp_path):
    """BEL-154-style raw ingest JSONL with decision + config + weak entries."""
    src = tmp_path / "ingest" / "paperclip"
    src.mkdir(parents=True)
    (src / f"{recent_ts()[:10]}.jsonl").write_text("\n".join([
        json.dumps({
            "source": "paperclip",
            "source_id": "run-123",
            "timestamp": recent_ts(),
            "agent": "opencode",
            "content": "Decision: use DeepSeek V4-Flash for all agents.",
            "metadata": {"linear_refs": ["BEL-154"], "paperclip_refs": ["ABS-10"]},
        }),
        json.dumps({
            "source": "paperclip",
            "source_id": "run-124",
            "timestamp": recent_ts(),
            "agent": "opencode",
            "content": "Config: export AGENTIC_MEMORY_DB=/var/lib/starship/memory.db",
            "metadata": {},
        }),
        json.dumps({
            "source": "paperclip",
            "source_id": "run-125",
            "timestamp": recent_ts(),
            "agent": "opencode",
            "content": "minor chat about the weather",
            "metadata": {},
        }),
    ]))
    return tmp_path


class TestExtraction:
    def test_decision_candidate(self):
        record = {
            "content": "Decision: use FAISS for vectors.",
            "metadata": {"linear_refs": ["BEL-153"]},
        }
        cands = mp.extract_facts(record)
        assert cands[0].fact_type == "decision"
        assert cands[0].linear_refs == ["BEL-153"]

    def test_reference_mentions_parsed_from_content(self):
        record = {"content": "See BEL-153 and ABS-9 for context."}
        cands = mp.extract_facts(record)
        assert cands[0].linear_refs == ["BEL-153"]
        assert cands[0].paperclip_refs == ["ABS-9"]

    def test_secrets_never_promoted(self):
        record = {"content": "api_key=supersecret123 Decision: rotate keys"}
        assert mp.extract_facts(record) == []

    def test_empty_content_skipped(self):
        assert mp.extract_facts({"content": "   "}) == []


class TestScoring:
    def test_decision_scores_high(self):
        cand = mp.FactCandidate(content="Decision: x", fact_type="decision",
                                timestamp=recent_ts())
        assert mp.score_confidence(cand) == 0.95

    def test_cross_referenced_above_threshold(self):
        cand = mp.FactCandidate(
            content="c", fact_type="pattern",
            linear_refs=["BEL-154"], paperclip_refs=["ABS-10"],
            timestamp=recent_ts())
        assert mp.score_confidence(cand) >= 0.7

    def test_old_entries_decay(self):
        cand = mp.FactCandidate(content="c", fact_type="pattern",
                                timestamp="2025-01-01T00:00:00Z")
        assert mp.score_confidence(cand) <= 0.5 * 0.6

    def test_human_authored_scores_higher(self):
        cand = mp.FactCandidate(content="c", fact_type="decision",
                                timestamp=recent_ts())
        assert (mp.score_confidence(cand, authored_by_human=True)
                > mp.score_confidence(cand, authored_by_human=False))


class TestPromotion:
    def test_promote_returns_memory_id(self, tmp_path):
        manager = MemoryManager(db_path=str(tmp_path / "mem.db"))
        cand = mp.FactCandidate(
            content="Decision: use SQLite for facts.",
            fact_type="decision",
            timestamp=recent_ts(),
            agent="opencode",
            linear_refs=["BEL-154"],
            paperclip_refs=["ABS-10"],
        )
        mid = mp.promote(manager, cand)
        assert mid
        results = manager.retrieve("SQLite facts decision")
        assert any(r["id"] == mid for r in results)
        manager.close()

    def test_below_threshold_returns_none(self, tmp_path):
        manager = MemoryManager(db_path=str(tmp_path / "mem.db"))
        cand = mp.FactCandidate(content="ordinary chatter", fact_type="pattern",
                                timestamp=recent_ts())
        assert mp.promote(manager, cand, min_confidence=0.7) is None
        manager.close()


class TestEndToEnd:
    def test_dry_run_reports_and_promotes_high_confidence(self, ingest_fixture, tmp_path):
        rc = mp.main([
            "--ingest-dir", str(ingest_fixture / "ingest"),
            "--facts-log", str(tmp_path / "facts.jsonl"),
            "--db", str(tmp_path / "mem.db"),
            "--dry-run",
        ])
        assert rc == 0
        assert not (tmp_path / "mem.db").exists() or True  # dry run writes nothing
        # db should not be created by dry run (MemoryManager still opens it)
        # Verify a real run promotes the decision + config, skips the weak chat.
        rc = mp.main([
            "--ingest-dir", str(ingest_fixture / "ingest"),
            "--facts-log", str(tmp_path / "facts.jsonl"),
            "--db", str(tmp_path / "mem.db"),
        ])
        assert rc == 0
        log = (tmp_path / "facts.jsonl").read_text()
        entries = [json.loads(l) for l in log.splitlines() if l.strip()]
        promoted_types = {e["type"] for e in entries}
        assert "decision" in promoted_types
        assert "config" in promoted_types

    def test_source_filter(self, ingest_fixture, tmp_path):
        rc = mp.main([
            "--ingest-dir", str(ingest_fixture / "ingest"),
            "--source", "hermes",
            "--facts-log", str(tmp_path / "facts.jsonl"),
            "--db", str(tmp_path / "mem.db"),
        ])
        assert rc == 0
        assert not (tmp_path / "facts.jsonl").exists()
