SHELL := /bin/bash
export PYTHONPATH := $(CURDIR):$(abspath $(CURDIR)/../../src/python)

# Prefer the monorepo venv python (has pytest) when present.
MONOREPO_VENV := $(abspath $(CURDIR)/../../.venv/bin/python)
PYTHON ?= $(if $(wildcard $(MONOREPO_VENV)),$(MONOREPO_VENV),python3)

.PHONY: test smoke

# Skeleton smoke: import the plugin shell + assert classification=plugin.
test:
	@$(PYTHON) -m pytest tests/test_skeleton.py -q

smoke: test
	@$(PYTHON) -c "import aspen_gatekeeper as g; assert g.classification == 'plugin'; assert callable(g.request_capability); print('aspen-gatekeeper: classification=plugin, gatekeeper imports OK')"
	@echo aspen-gatekeeper smoke ok