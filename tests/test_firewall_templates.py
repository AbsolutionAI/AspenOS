"""H-008 / ASP-372: OT/ICS-aware cell firewall rule templates (DRAFT).

Hermetic checker for the draft cell-perimeter firewall template files under
docs/security/firewall-templates/. It verifies the files exist, are UTF-8
text, carry the DRAFT / do-not-apply marker, and that the composed nftables
example keeps balanced brace/paren blocks.

This checker NEVER shells out to `nft` or `ufw` and never applies rules —
it is a static text existence/parse gate only, matching the board spec
("tests or a small checker that the template files exist and parse as text").
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL_DIR = ROOT / "docs" / "security" / "firewall-templates"
NFT_DIR = TPL_DIR / "nftables"

REQUIRED = [
    TPL_DIR / "README.md",
    NFT_DIR / "cell-base.nft",
    NFT_DIR / "cell-mqtt.nft",
    NFT_DIR / "cell-opcua.nft",
    NFT_DIR / "cell-ros2.nft",
    NFT_DIR / "cell-compose.example.nft",
]

# Every template file must be clearly marked so nobody mistakes it for a
# deployable ruleset (board: "comments must say DRAFT / do not apply").
DRAFT_MARKERS = ["DRAFT", "DO NOT APPLY"]


def _read(rel):
    path = ROOT / rel
    return path, path.read_text(encoding="utf-8")


def test_template_files_exist():
    for rel in REQUIRED:
        assert (ROOT / rel).is_file(), f"missing template file: {rel}"


def test_template_files_parse_as_text():
    for rel in REQUIRED:
        path, text = _read(rel)
        assert isinstance(text, str) and text.strip(), f"{rel} is empty"
        assert text.count("\n") >= 5, f"{rel} looks truncated (<5 lines)"


def test_draft_markers_present():
    for rel in REQUIRED:
        _, text = _read(rel)
        for marker in DRAFT_MARKERS:
            assert marker in text, (
                f"{rel} missing required marker {marker!r} "
                f"(templates must state DRAFT / DO NOT APPLY)"
            )


def test_compose_example_balanced_blocks():
    path, text = _read("docs/security/firewall-templates/nftables/cell-compose.example.nft")
    assert text.count("{") == text.count("}"), f"{path} unbalanced braces"
    assert text.count("(") == text.count(")"), f"{path} unbalanced parens"
    # Every defined variable is referenced somewhere in the example.
    defines = re.findall(r"^define (\w+)", text, re.M)
    assert defines, f"{path} has no per-cell variables to substitute"
    for var in defines:
        assert re.search(rf"\${var}\b", text), (
            f"{path} defines ${var} but never uses it"
        )


def test_checker_never_shells_out():
    """Guard against a future edit turning this test into a live apply."""
    path = Path(__file__)
    src = path.read_text(encoding="utf-8")
    # Built from fragments so the guard does not match its own ban list.
    banned = ("sub" + "process", "os.sys" + "tem", "os.pop" + "en", "shutil.wh" + "ich")
    for token in banned:
        assert token not in src, (
            f"{path.name} must not shell out to nft/ufw (found {token!r})"
        )


def test_placeholder_variables_used_in_fragments():
    """Each protocol fragment carries per-cell placeholders, not hardcoded IPs."""
    for name in ("cell-mqtt.nft", "cell-opcua.nft", "cell-ros2.nft"):
        path = NFT_DIR / name
        text = path.read_text(encoding="utf-8")
        assert "$" in text, f"{name} has no placeholder variables to substitute"