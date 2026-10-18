"""ASP-365 / H-017: committed NATS confs carry placeholders, never literal secrets.

AspenOS is a public repository and ``nats/server.conf`` is copied into
``/etc/starship/nats/`` by ``build-deb.sh`` / ``install-daemon.sh``. Any
``token:`` / ``password:`` value in ``nats/`` (including commented-out
examples) must be a ``__PLACEHOLDER__`` marker, an env reference, or a
template expression.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATS_DIR = ROOT / "nats"

_SECRET_KEY = re.compile(
    r"""\b(token|password|pass|nkey|seed)\s*[:=]\s*["']([^"']*)["']""", re.I
)
_ALLOWED = re.compile(r"^(__[A-Z0-9_]+__|\$[A-Za-z_][A-Za-z0-9_]*|\{\{.*\}\}|)$")


def _violations():
    out = []
    for path in sorted(NATS_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in {".conf", ".tmpl", ".yaml", ".yml"}:
            continue
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in _SECRET_KEY.finditer(line):
                if not _ALLOWED.match(m.group(2)):
                    # Never echo the value itself.
                    out.append(f"{path.relative_to(ROOT)}:{lineno} {m.group(1)}=<literal>")
    return out


def test_nats_confs_have_no_literal_secrets():
    assert _violations() == []


def test_detector_catches_a_literal(tmp_path, monkeypatch):
    fake = tmp_path / "nats"
    fake.mkdir()
    (fake / "x.conf").write_text('authorization { token: "not-a-placeholder" }\n')
    (fake / "y.conf").write_text('authorization { token: "__STARSHIP_NATS_TOKEN__" }\n')
    monkeypatch.setattr(sys.modules[__name__], "NATS_DIR", fake)
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    found = _violations()
    assert found == ["nats/x.conf:1 token=<literal>"]
