import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolver = _load_module("resolve_model_digests", SCRIPTS_DIR / "resolve-model-digests.py")
health_checker = _load_module("agent_health_checker", SCRIPTS_DIR / "agent-health-checker.py")


PIN_EVE = "sha256:4d1fe4fe01a49a9b476e275b2029cc5fdfc81779d12f86303d251a359228082b"
PINS = {
    "Eve-V2-Unleashed": {
        "alias": "Eve-V2-Unleashed",
        "upstream": "jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged:latest",
        "digest": PIN_EVE,
        "resolved": True,
    },
    "nomic-embed-text": {
        "alias": "nomic-embed-text",
        "upstream": "nomic-embed-text:latest",
        "digest": "sha256:0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f",
        "resolved": True,
    },
    "granite4.1-8b": {
        "alias": "granite4.1-8b",
        "upstream": "huihui_ai/granite4.1-abliterated:8b",
        "digest": "sha256:4b7d9eae0407925a746a6723b479cc1f780878bdce255c2ee1b669ded31b9f55",
        "resolved": True,
    },
}
MODELS = {k: {"alias": v["alias"], "upstream": v["upstream"]} for k, v in PINS.items()}


class TestNameAndDigestHelpers:
    def test_normalize_strips_latest(self):
        assert resolver.normalize_name("x:latest") == "x"
        assert resolver.normalize_name("x:7b") == "x:7b"

    def test_canon_digest(self):
        assert resolver.canon_digest("abc") == "sha256:abc"
        assert resolver.canon_digest("sha256:abc") == "sha256:abc"
        assert resolver.canon_digest("") == ""

    def test_split_ref(self):
        assert resolver.split_ref("jeffgreen311/pkg:latest") == ("jeffgreen311", "pkg", "latest")
        assert resolver.split_ref("nomic-embed-text") == ("library", "nomic-embed-text", "latest")
        assert resolver.split_ref("nomic-embed-text:7b") == ("library", "nomic-embed-text", "7b")
        assert resolver.split_ref("library/qwen:9b") == ("library", "qwen", "9b")


class TestFindPin:
    def test_by_key(self):
        assert resolver.find_pin(PINS, "Eve-V2-Unleashed")[0] == "Eve-V2-Unleashed"

    def test_by_upstream(self):
        matched = resolver.find_pin(
            PINS, "jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged:latest")
        assert matched[0] == "Eve-V2-Unleashed"

    def test_missing(self):
        assert resolver.find_pin(PINS, "nope") is None


class TestRender:
    def test_cmd_resolve_emits_valid_digests(self, monkeypatch, tmp_path):
        resolver_models = tmp_path / "models.yaml"
        resolver_models.write_text(
            "version: '2.1'\nmodels:\n  Eve-V2-Unleashed:\n    upstream: "
            "jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged:latest\n")
        out = tmp_path / "digests.yaml"
        monkeypatch.setattr(resolver, "api_tags_digests",
                            lambda: {"jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged":
                                     PIN_EVE})
        monkeypatch.setattr(resolver, "local_manifest_digests", lambda *a, **k: [])
        rc = resolver.cmd_resolve(resolver_models, out, offline=True)
        assert rc == 0
        import yaml
        doc = yaml.safe_load(out.read_text())
        pin = doc["models"]["Eve-V2-Unleashed"]
        assert pin["digest"] == PIN_EVE
        assert resolver.DIGEST_RE.match(pin["digest"])
        assert pin["resolved"] is True


class TestCheck:
    def _pins_doc(self):
        return {"models": {k: dict(v) for k, v in PINS.items()}}

    def test_clean_pins_pass_offline(self, tmp_path):
        pins = tmp_path / "pins.yaml"
        import yaml
        pins.write_text(yaml.safe_dump(self._pins_doc()))
        models = tmp_path / "models.yaml"
        models.write_text(yaml.safe_dump({"models": MODELS}))
        assert resolver.cmd_check(models, pins, offline=True) == 0

    def test_malformed_digest_fails(self, tmp_path):
        import yaml
        doc = self._pins_doc()
        doc["models"]["granite4.1-8b"]["digest"] = "not-a-digest"
        pins = tmp_path / "pins.yaml"
        pins.write_text(yaml.safe_dump(doc))
        models = tmp_path / "models.yaml"
        models.write_text(yaml.safe_dump({"models": MODELS}))
        assert resolver.cmd_check(models, pins, offline=True) == 1

    def test_missing_digest_fails_in_strict(self, tmp_path):
        import yaml
        doc = self._pins_doc()
        doc["models"] = {k: v for k, v in doc["models"].items() if k != "granite4.1-8b"}
        pins = tmp_path / "pins.yaml"
        pins.write_text(yaml.safe_dump(doc))
        models = tmp_path / "models.yaml"
        models.write_text(yaml.safe_dump({"models": MODELS}))
        assert resolver.cmd_check(models, pins, offline=True, strict=False) == 0
        assert resolver.cmd_check(models, pins, offline=True, strict=True) == 1


class TestCLI:
    def test_check_cli_rejects_drift(self, monkeypatch, tmp_path):
        import yaml
        tags_file = tmp_path / "tags.json"
        tags_file.write_text(json.dumps({"models": [
            {"name": "jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged:latest",
             "digest": PIN_EVE.split(":", 1)[1]},
        ]}))
        models_file = tmp_path / "models.yaml"
        models_file.write_text(yaml.safe_dump({"models": MODELS}))
        out = tmp_path / "digests.yaml"
        monkeypatch.setattr(resolver, "api_tags_digests",
                            lambda: {"jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged":
                                     PIN_EVE})
        monkeypatch.setattr(resolver, "local_manifest_digests", lambda *a, **k: [])
        rc = resolver.main(["--models", str(models_file), "--pins", str(out), "--offline"])
        assert rc == 0
        doc = yaml.safe_load(out.read_text())
        doc["models"]["Eve-V2-Unleashed"]["digest"] = "sha256:" + "f" * 64
        out.write_text(yaml.safe_dump(doc))
        monkeypatch.setattr(resolver, "registry_manifest",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
        rc = resolver.main(["--pins", str(out), "--check", "--offline"])
        assert rc == 1


class TestRepositoryPinFile:
    def test_committed_pins_file_exists_and_parseable(self):
        import yaml
        pins = PROJECT_ROOT / "config" / "models-digests.yaml"
        assert pins.is_file()
        doc = yaml.safe_load(pins.read_text())
        eve = doc["models"]["Eve-V2-Unleashed"]
        assert resolver.DIGEST_RE.match(eve["digest"])
        assert eve["resolved"] is True

    def test_eve_pin_is_local_revision(self):
        import yaml
        pins = PROJECT_ROOT / "config" / "models-digests.yaml"
        doc = yaml.safe_load(pins.read_text())
        eve = doc["models"]["Eve-V2-Unleashed"]
        assert eve["digest"] == PIN_EVE
        assert eve["source"] == "local"


class TestHealthCheckerGuards:
    def test_canon_digest(self):
        assert health_checker.canon_digest("abc") == "sha256:abc"
        assert health_checker.canon_digest("sha256:abc") == "sha256:abc"

    def test_pins_load_at_import(self):
        # Regression: pins must populate at import even though canon_digest is
        # defined in-module (ordering bug would leave them empty).
        assert health_checker.MODELS_DIGESTS
        pins, upstream = health_checker.MODELS_DIGESTS
        assert "Eve-V2-Unleashed" in pins

    def test_expected_digest_alias_lookup(self, monkeypatch):
        hc = health_checker
        old = hc.MODELS_DIGESTS
        hc.MODELS_DIGESTS = ({"Eve-V2-Unleashed": PIN_EVE},
                             {"jeffgreen311/Eve-V2-Unleashed-Qwen3.5-8B-Liberated-4K-4B-Merged:latest": PIN_EVE})
        try:
            assert hc.expected_digest("Eve-V2-Unleashed") == PIN_EVE
            assert hc.expected_digest("Eve-V2-Unleashed:latest") == PIN_EVE
            assert hc.expected_digest("nope") is None
        finally:
            hc.MODELS_DIGESTS = old

    def test_lookup_digest_matches_base_name(self):
        hc = health_checker
        assert hc.lookup_digest("nomic-embed-text", {"nomic-embed-text:latest": "b" * 64}) == "sha256:" + "b" * 64
        assert hc.lookup_digest("nope", {"nomic-embed-text:latest": "b" * 64}) is None