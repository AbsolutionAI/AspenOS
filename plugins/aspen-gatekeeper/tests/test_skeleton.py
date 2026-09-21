"""Smoke tests for the aspen-gatekeeper plugin skeleton (ASP-630).

Proves the thin plugin shell loads the monorepo gatekeeper (no fork), and that
the packaging metadata declares the ASP-628 classification (plugin) and a
matching manifest.
"""

import json
import os
import sys
import tomllib
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MONOREPO_SRC = PLUGIN_ROOT.parent.parent / "src" / "python"
sys.path.insert(0, str(MONOREPO_SRC))
sys.path.insert(0, str(PLUGIN_ROOT))


def test_plugin_imports_monorepo_gatekeeper():
    import aspen_gatekeeper

    assert aspen_gatekeeper.classification == "plugin"
    for name in (
        "request_capability",
        "authorize_gate_request",
        "forward_proposal",
        "NATSGateClient",
        "GatekeeperProxy",
        "SafetySubjectEnforcer",
    ):
        assert hasattr(aspen_gatekeeper, name), name


def test_plugin_reexports_gatekeeper_module():
    from gatekeeper import request_capability

    import aspen_gatekeeper

    assert aspen_gatekeeper.request_capability is request_capability


def test_pyproject_classification_is_plugin():
    with open(PLUGIN_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    assert pyproject["tool"]["aspen"]["classification"] == "plugin"
    assert pyproject["project"]["name"] == "aspen-gatekeeper"


def test_manifest_matches_metadata():
    with open(PLUGIN_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    with open(PLUGIN_ROOT / "manifest.json") as f:
        manifest = json.load(f)

    assert manifest["classification"] == "plugin"
    assert manifest["version"] == pyproject["project"]["version"]
    assert "capabilities" in manifest and manifest["capabilities"]
    assert "subjects" in manifest and manifest["subjects"]["subscribe"]
    assert "version" in manifest