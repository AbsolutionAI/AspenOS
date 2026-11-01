import json
import logging
import os
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("aspen-operator-registry")

DEFAULT_REGISTRY_PATH = "/var/lib/aspen/operator-registry.json"


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
        self._load()

    def _load(self):
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path) as f:
                data = json.load(f)
            for item in data:
                op = Operator(**item)
                self._operators[op.human_id] = op
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load operator registry: %s", e)

    def _persist(self):
        data = [asdict(op) for op in self._operators.values()]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

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
        if human_id in self._operators:
            existing = self._operators[human_id]
            if existing.status == "active":
                raise ValueError(f"Operator '{human_id}' is already enrolled and active")
        now = datetime.now(timezone.utc).isoformat()
        resolved = set()
        if aliases:
            for alias in aliases:
                alias = alias.strip()
                if not alias:
                    continue
                existing_op = self.find_by_alias(alias)
                if existing_op and existing_op.human_id != human_id:
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