"""H-020 package classification gate: ADR-0008 rule 4 enforcement.

Failure-mode tests point PACKAGE_ROOTS and PACKAGES_MD at a throwaway fixture
tree, so nothing here ever writes into the real plugins/ tree.
"""
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = str(REPO_ROOT / "scripts" / "check-package-classification.sh")

# A source of truth with a real tier row, so the agreement check has something
# to cross-check against.
FIXTURE_SOR = """# Fixture classification matrix

| Tier          | Examples        |
|---------------|-----------------|
| **Plugin**   | good-pkg, bad-tier-pkg, invalid-pkg, py-pkg |
| **Dev-only** | dev-pkg         |
"""

# name -> plugin.json body. Packages absent from this dict are undeclared.
FIXTURE_PACKAGES = {
    "good-pkg": {
        "name": "good-pkg",
        "version": "1.0.0",
        "description": "fixture: declares a valid tier that the SoR agrees with",
        "classification": "plugin",
    },
    "dev-pkg": {
        "name": "dev-pkg",
        "version": "1.0.0",
        "description": "fixture: declares a valid tier that the SoR agrees with",
        "classification": "dev-only",
    },
    "invalid-pkg": {
        "name": "invalid-pkg",
        "version": "1.0.0",
        "description": "fixture: classification is outside core/plugin/dev-only",
        "classification": "internal",
    },
    "bad-tier-pkg": {
        "name": "bad-tier-pkg",
        "version": "1.0.0",
        "description": "fixture: declares plugin, SoR says plugin only via this row",
        "classification": "dev-only",
    },
    "undeclared-pkg": {
        "name": "undeclared-pkg",
        "version": "1.0.0",
        "description": "fixture: classification deliberately absent",
    },
    "absent-pkg": {
        "name": "absent-pkg",
        "version": "1.0.0",
        "description": "fixture: declares a valid tier but is absent from the SoR",
        "classification": "plugin",
    },
}


def _run(pkg_root: Path, sor: Path, **kwargs):
    env = dict(os.environ)
    env["PACKAGE_ROOTS"] = str(pkg_root)
    env["PACKAGES_MD"] = str(sor)
    return subprocess.run(
        ["bash", SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        **kwargs,
    )


def _run_subset(tmp: Path, names):
    """Build a fixture tree holding only `names` and run the gate over it."""
    subset = tmp / "subset"
    subset.mkdir()
    for name in names:
        target = subset / name
        target.mkdir()
        (target / "plugin.json").write_text(
            json.dumps(FIXTURE_PACKAGES[name], indent=2) + "\n"
        )
    sor = subset / "PACKAGES.md"
    sor.write_text(FIXTURE_SOR)
    return _run(subset, sor)


def test_clean_repo_passes():
    """The real plugins/ tree declares a classification for every package."""
    result = subprocess.run(
        ["bash", SCRIPT], capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    assert result.returncode == 0, (
        f"H-020 gate failed on a compliant repo:\n{result.stdout}\n{result.stderr}"
    )


def test_compliant_fixture_passes():
    """A package declaring a valid tier that the SoR agrees with is accepted."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = _run_subset(tmp, ["good-pkg", "dev-pkg"])
        assert result.returncode == 0, (
            f"compliant fixture rejected:\n{result.stdout}\n{result.stderr}"
        )


def test_missing_declaration_detected():
    """ADR-0008 rule 4: a package with no `classification` fails the gate."""
    with tempfile.TemporaryDirectory() as td:
        result = _run_subset(Path(td), ["undeclared-pkg"])
        assert result.returncode != 0, "package with no classification was not detected"
        combined = result.stdout + result.stderr
        assert "undeclared-pkg" in combined, combined
        assert "no `classification` declared" in combined, combined


def test_invalid_value_detected():
    """A classification outside core/plugin/dev-only fails the gate."""
    with tempfile.TemporaryDirectory() as td:
        result = _run_subset(Path(td), ["invalid-pkg"])
        assert result.returncode != 0, "invalid classification value was not detected"
        combined = result.stdout + result.stderr
        assert "invalid-pkg" in combined, combined
        assert "is not one of" in combined, combined


def test_sor_coverage_detected():
    """A package absent from the classification source of truth fails."""
    with tempfile.TemporaryDirectory() as td:
        result = _run_subset(Path(td), ["absent-pkg"])
        assert result.returncode != 0, "package missing from the SoR was not detected"
        combined = result.stdout + result.stderr
        assert "absent-pkg" in combined, combined
        assert "not mentioned in" in combined, combined


def test_sor_disagreement_detected():
    """A declared tier that contradicts the SoR tier row fails the gate."""
    with tempfile.TemporaryDirectory() as td:
        result = _run_subset(Path(td), ["bad-tier-pkg"])
        assert result.returncode != 0, "SoR disagreement was not detected"
        combined = result.stdout + result.stderr
        assert "bad-tier-pkg" in combined, combined
        assert "classifies it as" in combined, combined


def test_dependency_named_classification_is_not_a_declaration():
    """A pyproject key nested under a dependency must not count as a declaration.

    Guards the reason the gate parses manifests with tomllib instead of grepping:
    `grep classification` would match this file and pass a package that declares
    nothing.
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pkg = tmp / "plugins" / "grep-trap-pkg"
        pkg.mkdir(parents=True)
        (pkg / "pyproject.toml").write_text(
            "[project]\n"
            'name = "grep-trap-pkg"\n'
            "dependencies = [\n"
            '  "classification-utils",\n'
            "]\n"
            "\n"
            "[project.optional-dependencies]\n"
            'lint = ["classification"]\n'
        )
        sor = tmp / "PACKAGES.md"
        sor.write_text(FIXTURE_SOR)
        result = _run(tmp / "plugins", sor)
        assert result.returncode != 0, (
            "a dependency named 'classification' was mistaken for a declaration:\n"
            f"{result.stdout}"
        )
        assert "no `classification` declared" in result.stdout, result.stdout


def test_nested_aspen_table_declaration_accepted():
    """[tool.aspen].classification is the declaration site for Python packages."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        pkg = tmp / "plugins" / "py-pkg"
        pkg.mkdir(parents=True)
        (pkg / "pyproject.toml").write_text(
            '[project]\nname = "py-pkg"\n\n[tool.aspen]\nclassification = "plugin"\n'
        )
        sor = tmp / "PACKAGES.md"
        sor.write_text(FIXTURE_SOR)
        result = _run(tmp / "plugins", sor)
        assert result.returncode == 0, (
            f"[tool.aspen] declaration not honoured:\n{result.stdout}\n{result.stderr}"
        )


def test_self_test_mode():
    """The --self-test flag passes (compliant accepted, undeclared rejected)."""
    result = subprocess.run(
        ["bash", SCRIPT, "--self-test"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"self-test failed:\n{result.stdout}\n{result.stderr}"
    )


def test_self_test_would_fail_on_a_no_op_gate():
    """The self-test must actually exercise the gate, not trivially pass.

    A detection-only self-test is satisfied by a gate that rejects everything, so
    this asserts the self-test is wired to a gate invocation whose behaviour it
    actually constrains: the repo's own script body must contain the detection
    message the self-test depends on.
    """
    body = Path(SCRIPT).read_text()
    assert "self-test: package with no classification was NOT detected" in body
    assert "self-test: a compliant package was rejected" in body
    # Both halves must be driven by run_gate, not by a hardcoded exit status.
    assert body.count("run_gate ") >= 3, "self-test lost its run_gate invocations"


def test_gate_is_executable():
    """Nightly section 23 asserts the gate is executable; keep the mode in git."""
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable"


def test_every_real_package_declares_a_valid_classification():
    """Independent of the shell gate: parse the real manifests and assert rule 4."""
    plugins = REPO_ROOT / "plugins"
    if not plugins.is_dir():
        pytest.skip("plugins/ does not exist")
    manifests = ("pyproject.toml", "plugin.json", "package.json", "Cargo.toml")
    valid = {"core", "plugin", "dev-only"}
    seen = []
    for pkg in sorted(p for p in plugins.iterdir() if p.is_dir()):
        if not any((pkg / m).is_file() for m in manifests):
            continue
        value = None
        if (pkg / "pyproject.toml").is_file():
            data = tomllib.loads((pkg / "pyproject.toml").read_text())
            value = (data.get("tool", {}).get("aspen", {}) or {}).get("classification")
        else:
            for name in ("plugin.json", "package.json"):
                if (pkg / name).is_file():
                    value = json.loads((pkg / name).read_text()).get("classification")
                    break
        assert value is not None, f"{pkg.name} declares no classification (ADR-0008 rule 4)"
        assert value in valid, f"{pkg.name} declares {value!r}, not one of {valid}"
        seen.append(pkg.name)
    assert seen, "no packages discovered under plugins/"
