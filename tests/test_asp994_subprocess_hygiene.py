"""ASP-994: root sweep must not shell out via os.system/os.popen or bare except.

Source assertions only. Do not import or execute the CI push script.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_staragent_uses_subprocess_not_os_system():
    text = (ROOT / "dashboard" / "server.py").read_text()
    assert "import subprocess" in text
    assert 'os.system("pgrep' not in text
    assert "os.system('pgrep" not in text
    assert (
        'subprocess.run(["pgrep", "-x", "staragent"], capture_output=True).returncode == 0'
        in text
    )


def test_push_ci_workflows_no_popen_no_bare_except():
    text = (ROOT / "scripts" / "push-ci-workflows.py").read_text()
    assert "os.popen" not in text
    assert "subprocess.run(" in text
    assert re.search(r"(?m)^\s*except\s*:", text) is None
    assert "except Exception:" in text
