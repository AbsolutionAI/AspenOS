import subprocess
import os
import tempfile
import shutil
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "check-no-devonly-in-prod.sh")

# Known Dev‑only markers from the real docs/PACKAGES.md
DEVONLY_MARKERS = [
    "aspen-package-mesh",
    "compound-engineering-gate-tools",
    "gatekeeper/minimal_shim.py",
]


def test_clean_production_surface():
    """Script exits 0 when no Dev‑only markers are present in production roots."""
    result = subprocess.run(
        ["bash", SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Script failed on clean repo:\n{result.stderr}"
    )


def test_devonly_marker_detected():
    """Script exits non‑zero when a Dev‑only marker file is placed under a production root."""
    # Create a temporary directory inside the debian/ production root
    prod_root = os.path.join(REPO_ROOT, "debian")
    if not os.path.isdir(prod_root):
        pytest.skip("debian/ directory does not exist – cannot plant marker")

    tmpdir = tempfile.mkdtemp(dir=prod_root, prefix=".devonly-test-")
    try:
        # Write a file containing one of the known markers
        marker_file = os.path.join(tmpdir, "planted.txt")
        with open(marker_file, "w") as f:
            f.write("aspen-package-mesh planted for test\n")

        result = subprocess.run(
            ["bash", SCRIPT],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            "Script should have failed when Dev‑only marker is present"
        )
        # The output should mention the offending marker
        assert "aspen-package-mesh" in result.stderr or "Dev-only" in result.stderr
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_self_test_mode():
    """The --self-test flag should pass (it plants a marker and expects detection)."""
    result = subprocess.run(
        ["bash", SCRIPT, "--self-test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Self‑test failed:\n{result.stderr}"
    )
