"""ASP-696 DoD: the phantom OSINT services stay gone, the real contract stays put.

`hybrid_intel` was a self-labelled no-op and `intel.html` was an unservable page
bound to an API that never existed. Deleting them was the fix; these tests are
what stops a later sweep from quietly reintroducing either one, and what keeps
the `osint-threat` skill honest about where OSINT actually lands (ADR-0007's
publish-only `aspen.sentinel.osint.ingest`).
"""

import ast
import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]

STUB_MODULE = ROOT / "src/python/services/hybrid_intel.py"
STUB_PAGE = ROOT / "src/python/lib/dashboard/intel.html"
SKILL_MD = ROOT / "src/python/lib/skills/osint-threat/SKILL.md"
SERVICES_DIR = ROOT / "src/python/services"

# The removed things, plus the two services the skill prose used to promise that
# never existed at all.
PHANTOMS = ("hybrid_intel", "HybridIntel", "osint_sensor", "/api/intel", "intel.html")

# Files allowed to name the phantoms, and why.
ALLOWED_REFERENCES = {
    # This file names them in order to assert their absence.
    "tests/test_osint_threat.py",
    # The skill's "Not this skill" guard: the deliberate negative reference.
    "src/python/lib/skills/osint-threat/SKILL.md",
    # The record of the removal.
    "docs/plans/ASP-696.md",
    "docs/solutions/asp-696-hybrid-intel-stub-removal.md",
}
ALLOWED_REFERENCE_GLOBS = ("docs/sweep-results-*.md",)

# The skill must not advertise capabilities or dependencies that do not resolve.
FORBIDDEN_SKILL_CLAIMS = ("hybrid_intel", "osint_sensor", "DECISION")


def _tracked_files():
    """Repo-relative paths of tracked files, or skip if git is unusable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"git ls-files unavailable: {exc}")
    return [p for p in out.split("\0") if p]


def _may_name_phantoms(rel: str) -> bool:
    if rel in ALLOWED_REFERENCES:
        return True
    return any(PurePosixPath(rel).match(g) for g in ALLOWED_REFERENCE_GLOBS)


def _read(rel: str):
    try:
        return (ROOT / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def test_hybrid_intel_module_stays_deleted():
    assert not STUB_MODULE.exists(), (
        "hybrid_intel was a 30-line no-op with zero importers; it must not return"
    )


def test_intel_dashboard_page_stays_deleted():
    # It sat beside server.py, outside STATIC_DIR, so no URL could ever serve it.
    assert not STUB_PAGE.exists(), "intel.html was unservable dead UI; it must not return"


def test_no_replacement_intel_engine_was_invented():
    names = [p.name for p in SERVICES_DIR.iterdir() if re.search(r"intel|osint", p.name)]
    assert not names, f"ASP-695 forbade building an OSINT engine, found: {names}"


def test_only_allowed_files_name_the_phantom_services():
    offenders = []
    for rel in _tracked_files():
        if _may_name_phantoms(rel):
            continue
        body = _read(rel)
        if body is None:
            continue
        hits = [p for p in PHANTOMS if p in body]
        if hits:
            offenders.append(f"{rel}: {', '.join(hits)}")
    assert not offenders, "live references to removed OSINT stubs:\n" + "\n".join(offenders)


def test_no_python_file_imports_the_removed_stub():
    offenders = []
    for rel in _tracked_files():
        if not rel.endswith(".py"):
            continue
        body = _read(rel)
        if body is None:
            continue
        try:
            tree = ast.parse(body)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any("hybrid_intel" in n for n in names):
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, "imports of the removed stub:\n" + "\n".join(offenders)


def test_osint_threat_skill_stays_registered():
    assert SKILL_MD.is_file(), SKILL_MD
    for manifest in ("src/python/lib/proxy.yaml", "agents/proxy.yaml"):
        assert "osint-threat" in _read(manifest), manifest


def test_skill_keeps_the_negative_guard_and_the_real_contract():
    body = SKILL_MD.read_text(encoding="utf-8")
    assert "## Not this skill" in body, "the negative-space guard was removed"
    assert "aspen.sentinel.osint.ingest" in body, "ADR-0007 subject must stay named"


def _advertised_body() -> str:
    """The skill minus its "Not this skill" guard.

    The guard must name the removed services in order to deny them, so it has
    to be excluded before asking whether the skill still advertises them.
    """
    body = SKILL_MD.read_text(encoding="utf-8")
    head, sep, _ = body.partition("## Not this skill")
    assert sep, "expected a '## Not this skill' section to exclude"
    return head


def _defined_memory_types():
    """Every spelling of every `MemoryType` member services/memory.py declares."""
    found = re.findall(
        r'^\s{4}([A-Z][A-Z_]*)\s*=\s*"([a-z_]+)"',
        (SERVICES_DIR / "memory.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    names = set()
    for member, value in found:
        names.update({member, member.lower(), member.title(), value, value.upper()})
    return names


def test_skill_promises_no_unresolvable_service_or_memory_type():
    """Capabilities and dependencies must name things that actually exist.

    The skill shipped `DECISION` (never a type) and advertised services that
    were never built. Verify against the definitions rather than against how
    plausible the names sound.
    """
    body = _advertised_body()
    for claim in FORBIDDEN_SKILL_CLAIMS:
        assert claim not in body, f"skill re-advertises non-existent {claim!r}"

    # Pull the actual storage claim out of the prose; do not guess from casing.
    claims = re.findall(r"\bas\s+(.+?)\s+memories\b", body)
    assert claims, f"no 'store findings as ... memories' claim found to verify in:\n{body}"

    defined = _defined_memory_types()
    assert defined, "could not parse MemoryType from services/memory.py"

    claimed = {t.strip().upper() for claim in claims for t in claim.split("/")}
    unknown = claimed - defined
    assert not unknown, f"skill claims memory types that do not exist: {sorted(unknown)}"
