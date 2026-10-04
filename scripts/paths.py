"""Host-relative path derivation for Aspen OS data.

Every default in this module resolves at call time from the environment, never
at import time. A module-level constant freezes whatever host imported it first,
which is what made the previous hardcoded ``/home/tech`` defaults untestable on
any other machine.

Precedence, highest first:

1. An explicit per-path environment override.
2. ``ASPEN_DATA_HOME`` / ``XDG_DATA_HOME`` for the Aspen data tree.
3. The invoking user's home directory.

The packaged deployment pins step 2 explicitly via
``Environment=ASPEN_DATA_HOME`` in ``systemd/agnetic-agent@.service``, so a
service running as a dedicated user does not depend on that user's home.

Refs: docs/plans/ASP-733.md
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str) -> Path | None:
    """Return ``$name`` as a Path, or None if unset/blank/not absolute-ish."""
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else None


def _home() -> Path:
    """The invoking user's home, via ``pwd`` when ``HOME`` is unset.

    ``Path.home()`` already falls back to the passwd database, but it consults
    ``HOME`` first and can be handed a value that does not exist. Normalising
    here keeps every caller on the same answer.
    """
    try:
        return Path(os.path.expanduser("~"))
    except (RuntimeError, KeyError):  # no HOME and no passwd entry
        return Path(os.sep)


def data_home() -> Path:
    """Root of the Aspen data tree. Default ``~/.aspen``."""
    explicit = _env_path("ASPEN_DATA_HOME")
    if explicit is not None:
        return explicit
    xdg = _env_path("XDG_DATA_HOME")
    if xdg is not None:
        return xdg / "starship"
    return _home() / ".aspen"


def hermes_agent_root() -> Path:
    """Hermes agent checkout. Default ``~/.hermes/hermes-agent``."""
    explicit = _env_path("HERMES_AGENT_ROOT")
    if explicit is not None:
        return explicit
    return _home() / ".hermes" / "hermes-agent"


def memory_ingest_dir() -> Path:
    """Raw BEL-154 ingest JSONL root. Default ``<data_home>/memory/ingest``."""
    explicit = _env_path("AGNETIC_MEMORY_INGEST_DIR")
    if explicit is not None:
        return explicit
    return data_home() / "memory" / "ingest"


def memory_facts_dir() -> Path:
    """Promoted-facts directory. Default ``<data_home>/memory/facts``."""
    explicit = _env_path("AGNETIC_MEMORY_FACTS_DIR")
    if explicit is not None:
        return explicit
    return data_home() / "memory" / "facts"


def memory_facts_log() -> Path:
    """Promoted-facts audit log. Default ``<memory_facts_dir>/facts.jsonl``."""
    return memory_facts_dir() / "facts.jsonl"


def holographic_db() -> Path:
    """Shared holographic SQLite. Default ``<data_home>/memory/holographic.db``."""
    explicit = _env_path("ASPEN_HOLOGRAPHIC_DB")
    if explicit is not None:
        return explicit
    return data_home() / "memory" / "holographic.db"
