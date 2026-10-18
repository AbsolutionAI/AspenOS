"""Durable vault approval gate for physical cell acts (H-022 / ASP-432).

Physical cell acts (ADR-0003 propose_act subjects) must be able to show a
*durable, human-reviewable* approval record before the gatekeeper mints a
capability. This module wires the existing HITL persistence
(``services/hitl.py`` HITLManager + ``services/hitl_vault.py`` HITLVault) into
the gatekeeper decision path:

1. ``ensure_vault_approval`` — at request time, insert a durable SQLite
   approval row and materialise an Obsidian vault note.
2. ``check_vault_approval`` — before grant, re-read the row; only status
   ``approved`` grants. Missing / pending / denied → **fail closed**.

Paths are resolved from ``HITL_DB`` / ``HITL_VAULT_DIR`` env at call time so
tests are hermetic (the same knob ``services/hitl_vault.py`` already uses). Any
vault-layer failure fails closed — the gatekeeper never silently grants.

Why load ``services/hitl*.py`` by explicit file path: the repo-root
``services/`` directory is shadowed by ``src/python/services`` (a regular
package that does *not* contain ``hitl.py``) whenever ``src/python`` is on
``sys.path``, which is always true for the gatekeeper daemon and its tests.
Loading the root module files explicitly keeps the single HITL implementation
authoritative without dragging the whole ``services`` package onto the path.
"""

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("gatekeeper.vault")

_HITL_MODULE_NAME = "_aspen_vault_services_hitl"
_HITL_VAULT_MODULE_NAME = "_aspen_vault_services_hitl_vault"

_SERVICES_DIR = Path(__file__).resolve().parents[3] / "services"

_hitl_mod: Any = None
_hitl_vault_mod: Any = None


def _load_module(name: str, filename: str) -> Any:
    """Load a root ``services/`` module under a private, clash-free name."""
    path = _SERVICES_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if spec.loader is None:
        raise ImportError(f"no loader for {path}")
    spec.loader.exec_module(module)
    return module


def _get_hitl_module() -> Any:
    global _hitl_mod
    if _hitl_mod is None:
        _hitl_mod = _load_module(_HITL_MODULE_NAME, "hitl.py")
    return _hitl_mod


def _get_hitl_vault_module() -> Any:
    global _hitl_vault_mod
    if _hitl_vault_mod is None:
        _hitl_vault_mod = _load_module(_HITL_VAULT_MODULE_NAME, "hitl_vault.py")
    return _hitl_vault_mod


def _resolve_hitl_paths() -> Tuple[Path, Path]:
    """Resolve the HITL DB + vault dir from env at call time.

    ``HITL_DB`` / ``HITL_VAULT_DIR`` are honored per call (hermetic tests).
    Fallbacks mirror the root ``services`` implementations: the shared
    ``services.hitl`` DB location and the vault module's default vault dir.
    """
    hitl = _get_hitl_module()
    db_env = os.environ.get("HITL_DB")
    db_path = Path(db_env) if db_env else Path(hitl.DB_PATH)
    vault_env = os.environ.get("HITL_VAULT_DIR")
    vault_dir = Path(vault_env) if vault_env else Path(_get_hitl_vault_module().VAULT_DIR)
    return db_path, vault_dir


def _point_hitl_db(db_path: Path) -> None:
    """Route the shared HITLManager store to the resolved DB.

    ``services.hitl`` computes its module-level DB path at import and has no
    per-instance override, while ``services.hitl_vault`` already honors
    ``HITL_DB``. Pointing the shared store at the same env knob keeps the two
    layers consistent (one operator knob) without touching prod defaults when
    the env is unset.
    """
    if "HITL_DB" in os.environ:
        hitl = _get_hitl_module()
        hitl.DB_DIR = db_path.parent
        hitl.DB_PATH = db_path


def make_manager() -> Any:
    """Return a fresh HITLManager bound to the resolved HITL DB."""
    db_path, _ = _resolve_hitl_paths()
    _point_hitl_db(db_path)
    hitl = _get_hitl_module()
    return hitl.HITLManager(dict(hitl.DEFAULT_CONFIG))


def make_vault() -> Any:
    """Return a fresh HITLVault bound to the resolved paths."""
    db_path, vault_dir = _resolve_hitl_paths()
    return _get_hitl_vault_module().HITLVault(vault_dir=vault_dir, hitl_db=db_path)


def ensure_vault_approval(
    request_id: str,
    capability: str,
    resource: str,
    profile: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Create a durable vault approval record for a physical cell act.

    Inserts a persistent SQLite approval row (HITLManager.create_request) and
    materialises the Obsidian note (HITLVault.sync). Returns
    ``{hitl_request_id, note_id, status}`` so the gate can re-check before
    grant. Raises on any vault-layer failure — callers fail closed.
    """
    db_path, _vault_dir = _resolve_hitl_paths()
    _point_hitl_db(db_path)

    manager = _get_hitl_module().HITLManager(dict(_get_hitl_module().DEFAULT_CONFIG))
    req = manager.create_request(
        tool="propose_act",
        arguments={"resource": resource},
        agent=agent_id,
        context={
            "request_id": request_id,
            "profile": profile,
            "physical": True,
        },
    )

    make_vault().sync()

    return {
        "hitl_request_id": req.id,
        "note_id": req.id,
        "status": req.status,
    }


def check_vault_approval(hitl_request_id: Optional[str], note_id: Optional[str]) -> bool:
    """Return True only when the vault record is durable and approved.

    Fail-closed checks, in order:
    - the SQLite approval row exists and its status is ``approved``;
    - the reviewable Obsidian note is present (so a human can actually see it).
    Any exception or missing piece → False.
    """
    try:
        if not hitl_request_id:
            return False
        req = make_manager().get_request(hitl_request_id)
        if req is None or req.status != "approved":
            return False
        if note_id:
            note = make_vault().get(note_id)
            if note is None:
                return False
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("vault check failed: %s", exc)
        return False