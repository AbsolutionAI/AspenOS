import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("aspen-operator-registry")

DEFAULT_REGISTRY_PATH = "/var/lib/aspen/operator-registry.json"

_DEFAULT_FILE_MODE = 0o600


@dataclass
class Operator:
    human_id: str
    display_name: str
    enrolled_at: str = ""
    enrolled_by: str = ""
    aliases: list[str] = field(default_factory=list)
    status: str = "active"
    plant_id: str = ""


class OperatorRegistry:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_REGISTRY_PATH
        self._operators: dict[str, Operator] = {}
        self._load_error = False
        self._load()

    def _load(self):
        self._load_error = False
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path) as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("registry must be a JSON array")
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("registry items must be objects")
                op = Operator(**item)
                self._operators[op.human_id] = op
        except (json.JSONDecodeError, IOError, OSError, TypeError, ValueError) as e:
            logger.error("Failed to load operator registry: %s", e)
            self._load_error = True
            self._operators = {}

    def _persist(self):
        if self._load_error:
            raise RuntimeError("registry file is corrupt, refusing to write")
        data = [asdict(op) for op in self._operators.values()]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        tmp = self.db_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(tmp, _DEFAULT_FILE_MODE)
        os.replace(tmp, self.db_path)

    def _find_by_casefold(self, value: str) -> Optional[Operator]:
        folded = value.strip().lower()
        for op in self._operators.values():
            if op.human_id.lower() == folded:
                return op
            if folded in [a.lower() for a in op.aliases]:
                return op
        return None

    def enroll(
        self,
        human_id: str,
        display_name: str,
        enrolled_by: str = "",
        aliases: Optional[list[str]] = None,
        plant_id: str = "",
    ) -> Operator:
        human_id = human_id.strip()
        if not human_id:
            raise ValueError("human_id must not be empty")
        existing = self._find_by_casefold(human_id)
        if existing is not None:
            if existing.human_id == human_id:
                if existing.status == "active":
                    raise ValueError(f"Operator '{human_id}' is already enrolled and active")
            else:
                raise ValueError(
                    f"Operator '{human_id}' (case-fold match for '{existing.human_id}') is already enrolled"
                )
        now = datetime.now(timezone.utc).isoformat()
        resolved = set()
        if aliases:
            for alias in aliases:
                alias = alias.strip()
                if not alias:
                    continue
                existing_op = self._find_by_casefold(alias)
                if existing_op is not None:
                    raise ValueError(
                        f"Alias '{alias}' is already bound to operator '{existing_op.human_id}'"
                    )
                resolved.add(alias)
        op = Operator(
            human_id=human_id,
            display_name=display_name,
            enrolled_at=now,
            enrolled_by=enrolled_by,
            aliases=sorted(resolved),
            status="active",
            plant_id=plant_id,
        )
        self._operators[human_id] = op
        self._persist()
        logger.info("Enrolled operator '%s' (human_id=%s)", display_name, human_id)
        return op

    def revoke(self, human_id: str) -> bool:
        op = self._operators.get(human_id)
        if op is None:
            logger.warning("Revoke failed: operator '%s' not found", human_id)
            return False
        if op.status != "active":
            logger.info("Operator '%s' is already %s", human_id, op.status)
            return True
        op.status = "revoked"
        self._persist()
        logger.info("Revoked operator '%s' (human_id=%s)", op.display_name, human_id)
        return True

    def get(self, human_id: str) -> Optional[Operator]:
        return self._operators.get(human_id)

    def find_by_alias(self, alias: str) -> Optional[Operator]:
        alias = alias.strip().lower()
        for op in self._operators.values():
            if alias in [a.lower() for a in op.aliases]:
                return op
        return None

    def list(self, active_only: bool = True) -> list[Operator]:
        if active_only:
            return [op for op in self._operators.values() if op.status == "active"]
        return list(self._operators.values())