#!/usr/bin/env python3
"""Best-effort write of a BEL-154 ingest record into shared holographic SQLite.

Failure isolation: never raise to the caller. Tests using a temp ``ingest_dir``
do not touch production unless ``ASPEN_HOLOGRAPHIC_DB`` is set.

DB default: /home/tech/.aspen/memory/holographic.db
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
import types
from pathlib import Path

DEFAULT_HOLOGRAPHIC_DB = Path("/home/tech/.aspen/memory/holographic.db")
_HERMES_AGENT = Path(
    os.environ.get("HERMES_AGENT_ROOT", "/home/tech/.hermes/hermes-agent")
)
_MAX_FACT_CHARS = 2000
_MIN_FACT_CHARS = 8


def _should_write(ingest_dir: Path | None, default_ingest_dir: Path | None) -> bool:
    if os.environ.get("ASPEN_HOLOGRAPHIC_DISABLE") == "1":
        return False
    if os.environ.get("ASPEN_HOLOGRAPHIC_DB"):
        return True
    if ingest_dir is None or default_ingest_dir is None:
        return True
    try:
        return Path(ingest_dir).resolve() == Path(default_ingest_dir).resolve()
    except OSError:
        return False


def _compose_fact(
    content: str,
    *,
    source: str,
    source_id: str,
    agent: str,
    project: str | None,
) -> str:
    head = f"[{source}/{source_id} agent={agent}"
    if project:
        head += f" project={project}"
    head += "] "
    body = (content or "").strip()
    fact = (head + body)[:_MAX_FACT_CHARS]
    return fact


def _tags(
    source: str,
    agent: str,
    project: str | None,
    linear_refs: list[str] | None,
    paperclip_refs: list[str] | None,
) -> str:
    parts = [source, agent]
    if project:
        parts.append(project)
    for ref in (linear_refs or []) + (paperclip_refs or []):
        if ref:
            parts.append(ref)
    # FTS5 hyphen split — also keep unhyphenated tokens
    extra = []
    for p in list(parts):
        extra.extend(tok for tok in p.replace("-", " ").split() if tok and tok not in parts)
    return ",".join(dict.fromkeys(parts + extra))


def _category(content: str) -> str:
    c = (content or "").lstrip().lower()
    if c.startswith("decision"):
        return "decision"
    if c.startswith("reference"):
        return "reference"
    return "ingest"


# Successful loads cache the module; failed loads cache the exception and
# re-raise it on every later call. A present-but-broken plugin must hard-fail
# every time (ASP-781 plan); only an absent plugin returns None.
_MODULE_CACHE: dict[str, types.ModuleType | BaseException] = {}


def catalog_plugin_dir() -> Path | None:
    env = os.environ.get("ASPEN_HOLOGRAPHIC_PLUGIN")
    if env:
        candidate = Path(env)
        if not _reject_catalog(candidate) and _is_valid_catalog(candidate):
            return candidate.resolve()
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        candidate = Path(hermes_home) / "plugins" / "holographic"
        if _is_valid_catalog(candidate) and not _reject_catalog(candidate):
            return candidate.resolve()
    home = os.environ.get("HOME", "")
    if home.startswith("/home/tech/.hermes/"):
        home = "/home/tech"
    candidate = Path(home) / ".hermes" / "plugins" / "holographic"
    if _is_valid_catalog(candidate) and not _reject_catalog(candidate):
        return candidate.resolve()
    raise ImportError(
        "No valid holographic catalog plugin directory found — "
        "holographic read-back NOT verified"
    )


def _is_valid_catalog(d: Path) -> bool:
    return (
        d.is_dir()
        and (d / "store.py").is_file()
        and (d / "holographic.py").is_file()
        and (d / "text.py").is_file()
    )


def _reject_catalog(d: Path) -> bool:
    s = str(d)
    return "/plugin-sources/holographic-" in s or "/plugins/memory/holographic" in s


def load_memory_store() -> object | None:
    try:
        catalog_dir = catalog_plugin_dir()
    except ImportError:
        print("holographic read-back NOT verified", file=sys.stderr)
        return None
    cache_key = str(catalog_dir)
    if cache_key in _MODULE_CACHE:
        cached = _MODULE_CACHE[cache_key]
        if isinstance(cached, BaseException):
            raise cached
        return cached.MemoryStore
    try:
        if str(_HERMES_AGENT) not in sys.path:
            sys.path.insert(0, str(_HERMES_AGENT))
        pkg_name = "aspen_holographic_catalog"
        suffix = cache_key.replace("/", "_").replace("-", "_").replace(".", "_")
        full_pkg = f"{pkg_name}_{suffix}"
        spec = importlib.machinery.ModuleSpec(full_pkg, None)
        pkg = types.ModuleType(spec.name)
        pkg.__path__ = [str(catalog_dir)]
        pkg.__spec__ = spec
        pkg.__package__ = spec.name
        sys.modules[spec.name] = pkg

        def _load_submodule(name: str) -> types.ModuleType:
            sub_spec = importlib.util.spec_from_file_location(
                f"{spec.name}.{name}", str(catalog_dir / f"{name}.py"),
                submodule_search_locations=pkg.__path__,
            )
            if sub_spec is None:
                raise ImportError(f"Could not load {name}.py from {catalog_dir}")
            mod = importlib.util.module_from_spec(sub_spec)
            mod.__package__ = spec.name
            sys.modules[sub_spec.name] = mod
            sub_spec.loader.exec_module(mod)
            return mod

        _load_submodule("holographic")
        _load_submodule("text")
        store_module = _load_submodule("store")
        _MODULE_CACHE[cache_key] = store_module
        return store_module.MemoryStore
    except Exception as exc:
        _MODULE_CACHE[cache_key] = exc
        raise

def write_holographic(
    content: str,
    *,
    source: str,
    source_id: str = "",
    agent: str = "",
    project: str | None = None,
    linear_refs: list[str] | None = None,
    paperclip_refs: list[str] | None = None,
    ingest_dir: Path | None = None,
    default_ingest_dir: Path | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Insert a fact. Returns fact_id or None. Never raises."""
    try:
        if not _should_write(ingest_dir, default_ingest_dir):
            return None
        body = (content or "").strip()
        if len(body) < _MIN_FACT_CHARS:
            return None
        fact = _compose_fact(
            body, source=source, source_id=source_id or "unknown",
            agent=agent or source, project=project,
        )
        tags = _tags(source, agent or source, project, linear_refs, paperclip_refs)
        category = _category(body)
        db = Path(db_path) if db_path else Path(
            os.environ.get("ASPEN_HOLOGRAPHIC_DB", str(DEFAULT_HOLOGRAPHIC_DB))
        )
        MemStore = load_memory_store()
        if MemStore is None:
            return None
        store = MemStore(db_path=str(db))
        return int(store.add_fact(fact, category=category, tags=tags))
    except Exception as exc:  # isolation
        print(f"holographic-ingest: skipped: {exc}", file=sys.stderr)
        return None
