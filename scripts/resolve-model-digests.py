#!/usr/bin/env python3
"""Starship OS — resolve and pin Ollama model digests (F-013 / ASP-377).

Ollama tags (:latest, :7b) are mutable pointers; this tool pins model
revisions by the sha256 of their OCI manifest and enforces integrity on the
local cell without relying on digest-pinned pull refs (which Ollama 0.32.11
rejects: ``invalid model name``). Enforcement is *verify-after-pull*:
install-models.sh / agent-health-checker.py / dashboard pull by tag, then
compare the pulled model's digest against its pin and refuse to use it on
mismatch.

Usage:
  python3 scripts/resolve-model-digests.py                 # (re)generate pins
  python3 scripts/resolve-model-digests.py --check         # validate pins
  python3 scripts/resolve-model-digests.py --check --offline   # structural only
  python3 scripts/resolve-model-digests.py --digest NAME   # print a pin (exit 1 if none)
  python3 scripts/resolve-model-digests.py --verify-local NAME  # compare local copy

Resolution precedence (default):
  1. local Ollama store (/api/tags digest, or the sha256 of the stored
     registry.ollama.ai manifest JSON) — the revision this cell owns and
     verifies against
  2. registry manifest from registry.ollama.ai (fallback for models not yet
     present locally; digest is sha256 of the manifest document)
--check reports drift between local pins and registry HEAD as a warning
(upstream tag moved on); with --strict that drift is a hard error.

Environment:
  OLLAMA_URL               Ollama server base URL (default http://127.0.0.1:11434)
  OLLAMA_MODELS            Ollama models dir (default $HOME/.ollama/models)
  STARSHIP_MODELS_YAML     models.yaml override (default config/models.yaml)
  STARSHIP_PINS_YAML       models-digests.yaml override (default config/models-digests.yaml)
  STARSHIP_REGISTRY        registry base URL (default https://registry.ollama.ai)
  STARSHIP_STRICT_DIGESTS  when "1", missing pins are a hard error in --check
  STARSHIP_OFFLINE         when "1", force offline (no registry / api access)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_YAML = Path(os.getenv(
    "STARSHIP_MODELS_YAML", str(PROJECT_DIR / "config" / "models.yaml")))
DEFAULT_PINS_YAML = Path(os.getenv(
    "STARSHIP_PINS_YAML", str(PROJECT_DIR / "config" / "models-digests.yaml")))
REGISTRY = os.getenv("STARSHIP_REGISTRY", "https://registry.ollama.ai").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
STRICT = os.getenv("STARSHIP_STRICT_DIGESTS", "0") == "1"
OFFLINE = os.getenv("STARSHIP_OFFLINE", "0") == "1"

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def p_err(msg):
    sys.stderr.write(msg + "\n")


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        p_err("ERROR: PyYAML is required to parse %s" % path)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception as exc:
        p_err("ERROR: cannot parse %s: %s" % (path, exc))
        sys.exit(1)


def dump_yaml(data):
    import yaml
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)


def normalize_name(name):
    """Strip a trailing :latest tag for stable matching."""
    name = (name or "").strip()
    if name.endswith(":latest"):
        return name[: -len(":latest")]
    return name


def canon_digest(digest):
    """Canonical sha256:<hex> form (tolerates /api/tags bare-hex digests)."""
    digest = (digest or "").strip()
    if digest and not digest.startswith("sha256:"):
        return "sha256:" + digest
    return digest


def split_ref(ref):
    """Split an upstream ref into (namespace, repo, tag)."""
    base, tag = ref, "latest"
    if ":" in ref:
        base, tag = ref.rsplit(":", 1)
    base = base.split("@", 1)[0]
    if base.startswith("library/"):
        base = base[len("library/"):]
    if "/" in base:
        ns, repo = base.split("/", 1)
    else:
        ns, repo = "library", base
    return ns, repo, tag


def models_dir():
    return Path(os.getenv("OLLAMA_MODELS", str(Path.home() / ".ollama" / "models")))


def repo_manifest_dir(mdir, ns, repo):
    return mdir / "manifests" / "registry.ollama.ai" / ns / repo


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def local_manifest_digests(mdir, ns, repo):
    """Return [(digest, filename), ...] for every manifest under a model dir."""
    root = repo_manifest_dir(mdir, ns, repo)
    if not root.is_dir():
        return []
    out = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        try:
            data = f.read_bytes()
        except OSError:
            continue
        out.append(("sha256:" + sha256_hex(data), f.name))
    return out


def api_tags_digests(url=OLLAMA_URL, offline=False):
    """Return {normalized name: digest} from the Ollama /api/tags endpoint."""
    if offline:
        return {}
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=5) as resp:
            data = json.load(resp)
    except Exception as exc:
        p_err("note: /api/tags unreachable (%s)" % exc)
        return {}
    out = {}
    for m in data.get("models", []):
        out[normalize_name(m.get("name", ""))] = canon_digest(m.get("digest", ""))
    return out


def registry_manifest(ns, repo, tag, timeout=20):
    """Fetch a registry manifest; digest is sha256 of the response body."""
    url = f"{REGISTRY}/v2/{ns}/{repo}/manifests/{tag}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return "sha256:" + sha256_hex(body), body


def resolve_digest(upstream, offline=OFFLINE):
    """Return (digest, source) for an upstream ref; (None, None) if unresolvable.

    Local store first (it is the revision this cell owns and verifies against),
    then the registry for models not yet present. A cell may legitimately run an
    older pinned revision than the registry's current HEAD; that drift is
    reported as a warning by --check rather than treated as tampering.
    """
    ns, repo, tag = split_ref(upstream)
    cands = local_manifest_digests(models_dir(), ns, repo)
    if cands:
        by_name = {name: digest for digest, name in cands}
        if tag in by_name:
            return by_name[tag], "local"
        return cands[0][0], "local"
    tags = api_tags_digests()
    for key, digest in tags.items():
        if key == normalize_name(upstream):
            return canon_digest(digest), "local"
    if not offline:
        try:
            digest, _ = registry_manifest(ns, repo, tag)
            return digest, "registry"
        except Exception as exc:
            p_err("note: registry lookup failed for %s: %s" % (upstream, exc))
    return None, None


def load_models(path=None):
    cfg = load_yaml(path or DEFAULT_MODELS_YAML)
    return cfg.get("models", {}) if isinstance(cfg, dict) else {}


def load_pins(path=None):
    cfg = load_yaml(path or DEFAULT_PINS_YAML)
    return cfg.get("models", {}) if isinstance(cfg, dict) else {}


def find_pin(pins, name):
    """Match a model name against pins by key, alias, upstream, plain upstream."""
    if not isinstance(pins, dict):
        return None
    if name in pins:
        return name, pins[name]
    for key, pin in pins.items():
        pin = pin or {}
        upstream = str(pin.get("upstream", ""))
        plain = upstream.split("@", 1)[0]
        if upstream == name or plain == name or pin.get("alias") == name:
            return key, pin
    return None


def cmd_resolve(models_path, pins_path, offline):
    models = load_models(models_path)
    if not models:
        p_err("ERROR: no models found in config/models.yaml")
        return 1
    pins, failures = {}, 0
    for name, meta in models.items():
        meta = meta or {}
        upstream = meta.get("upstream")
        if not upstream:
            continue
        digest, source = resolve_digest(upstream, offline=offline)
        if not digest:
            failures += 1
            p_err("WARN: no resolveable digest for %s (%s)" % (name, upstream))
        pins[name] = {
            "alias": meta.get("alias", name),
            "upstream": upstream,
            "digest": digest,
            "source": source or "unresolved",
            "resolved": bool(digest),
        }
    doc = {
        "version": "2.1-f013",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Generated by scripts/resolve-model-digests.py — do not hand-edit. "
                 "digest is sha256 of the OCI manifest; verify-after-pull is enforced "
                 "by install-models.sh / agent-health-checker.py / dashboard."),
        "models": pins,
    }
    pins_path.parent.mkdir(parents=True, exist_ok=True)
    pins_path.write_text(dump_yaml(doc))
    print("wrote %s (%d models, %d pinned)" % (pins_path, len(pins), len(pins) - failures))
    print("NOTE: unpinned: %s" % ", ".join(sorted(
        n for n, p in pins.items() if not p.get("resolved"))) or "none")
    return 0


def cmd_check(models_path, pins_path, offline, strict=STRICT):
    models = load_models(models_path)
    pins = load_pins(pins_path)
    errors, warns = [], []
    strict = bool(strict or STRICT)

    if not isinstance(pins, dict):
        p_err("ERROR: pins config is not a mapping")
        return 1

    for key, pin in pins.items():
        pin = pin or {}
        digest = pin.get("digest")
        upstream = str(pin.get("upstream", ""))
        if not digest or not isinstance(digest, str):
            errors.append("%s: missing digest" % key)
            continue
        if not DIGEST_RE.match(digest):
            errors.append("%s: malformed digest %r" % (key, digest))
            continue
        if not upstream:
            errors.append("%s: missing upstream" % key)

    for name, meta in models.items():
        meta = meta or {}
        upstream = meta.get("upstream")
        if not upstream:
            continue
        matched = find_pin(pins, name)
        if not matched:
            msg = "%s: no digest pin (%s)" % (name, upstream)
            errors.append(msg) if strict else warns.append(msg)
            continue
        _, pin = matched
        if not pin.get("resolved") or not pin.get("digest"):
            msg = "%s: pin present but unresolved" % name
            errors.append(msg) if strict else warns.append(msg)

    if not offline:
        for key, pin in pins.items():
            pin = pin or {}
            upstream = str(pin.get("upstream", ""))
            digest = pin.get("digest")
            if not digest or not DIGEST_RE.match(str(digest)) or not upstream:
                continue
            ns, repo, tag = split_ref(upstream)
            try:
                now, _ = registry_manifest(ns, repo, tag)
            except Exception as exc:
                warns.append("%s: registry unreachable, skipping drift check (%s)"
                             % (key, exc))
                continue
            if now != digest:
                msg = (
                    "%s: local pin %s differs from registry HEAD for %s (%s); "
                    "the cell runs a pinned older revision. Re-run the resolver "
                    "to adopt the new revision." % (key, digest, upstream, now))
                errors.append(msg) if strict else warns.append(msg)

    code = 0
    for msg in errors:
        p_err("ERROR: %s" % msg)
        code = 1
    for msg in warns:
        p_err("WARN: %s" % msg)
    if code:
        p_err("FAIL: model digest pins are invalid (F-013)")
    else:
        print("OK: %d model digest pins validated (F-013)" % len(pins))
    return code


def cmd_digest(name, pins_path):
    if not name:
        p_err("ERROR: --digest requires a model name")
        return 1
    pins = load_pins(pins_path)
    matched = find_pin(pins, name)
    if not matched:
        p_err("ERROR: %s has no digest pin" % name)
        return 1
    digest = matched[1].get("digest")
    if not digest or not DIGEST_RE.match(str(digest)):
        p_err("ERROR: %s pin exists but is unresolved" % matched[0])
        return 1
    print(digest)
    return 0


def cmd_verify_local(name, pins_path, offline):
    pins = load_pins(pins_path)
    matched = find_pin(pins, name)
    if not matched:
        p_err("ERROR: %s has no digest pin" % name)
        return 3
    digest = matched[1].get("digest")
    upstream = str(matched[1].get("upstream", name))
    if not digest or not DIGEST_RE.match(str(digest)):
        p_err("ERROR: %s pin is unresolved" % matched[0])
        return 3
    ns, repo, _ = split_ref(upstream)
    cands = local_manifest_digests(models_dir(), ns, repo)
    for cand, fname in cands:
        if cand == digest:
            print("OK: %s local revision matches %s" % (name, digest))
            return 0
    if cands:
        p_err("FAIL: %s local manifest %s != pinned %s" % (name, cands[0][0], digest))
        return 1
    if offline:
        p_err("ERROR: %s not present locally (offline, no manifest)" % name)
        return 2
    tags = api_tags_digests()
    got = tags.get(normalize_name(upstream)) or tags.get(normalize_name(name))
    if got:
        if got == digest:
            print("OK: %s local revision matches %s" % (name, digest))
            return 0
        p_err("FAIL: %s local digest %s != pinned %s" % (name, got, digest))
        return 1
    ids = ollama_list_ids()
    oid = ids.get(normalize_name(upstream)) or ids.get(normalize_name(name))
    if oid:
        if digest.split(":", 1)[1].startswith(oid):
            print("OK: %s local revision matches %s" % (name, digest))
            return 0
        p_err("FAIL: %s ollama id %s != pinned %s" % (name, oid, digest))
        return 1
    p_err("ERROR: %s not present locally (no manifest, no /api/tags entry)" % name)
    return 2


def ollama_list_ids():
    try:
        out = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    ids = {}
    for line in out.stdout.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) >= 2:
            ids[parts[0]] = parts[1]
    return ids


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="resolve-model-digests.py",
        description="Resolve, pin and verify Ollama model digests (F-013).")
    ap.add_argument("--models", default=str(DEFAULT_MODELS_YAML),
                    help="models.yaml source (default: %(default)s)")
    ap.add_argument("--pins", default=str(DEFAULT_PINS_YAML),
                    help="models-digests.yaml target (default: %(default)s)")
    ap.add_argument("--offline", action="store_true",
                    help="never hit registry or /api/tags (local manifests only)")
    ap.add_argument("--strict", action="store_true",
                    help="treat missing pins as errors in --check")
    ap.add_argument("--check", action="store_true",
                    help="validate config/models-digests.yaml")
    ap.add_argument("--digest", metavar="NAME",
                    help="print the pinned digest for a model name")
    ap.add_argument("--verify-local", metavar="NAME",
                    help="verify a local model against its pin")
    args = ap.parse_args(argv)
    models_path = Path(args.models)
    pins_path = Path(args.pins)
    offline = OFFLINE or args.offline
    if args.check:
        return cmd_check(models_path, pins_path, offline, args.strict)
    if args.digest:
        return cmd_digest(args.digest, pins_path)
    if args.verify_local:
        return cmd_verify_local(args.verify_local, pins_path, offline)
    return cmd_resolve(models_path, pins_path, offline)


if __name__ == "__main__":
    sys.exit(main())