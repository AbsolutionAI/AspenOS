"""
aspen-gatekeeper — ADR-0008 plugin shell over the monorepo gatekeeper.

Source of truth stays at ``src/python/gatekeeper/`` until package extract (ASP-628
decision); this package is a thin, loadable plugin that imports and re-exports it.
Running the plugin (or its tests) requires monorepo ``src/python`` on ``PYTHONPATH``;
``make smoke`` wires that up automatically.
"""

from gatekeeper import __all__ as _MONOREPO_ALL
from gatekeeper import *  # noqa: F401,F403

__version__ = "0.1.0"

__all__ = _MONOREPO_ALL + ["__version__", "classification"]

classification = "plugin"