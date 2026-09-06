"""Read-only adapter for real Entire checkpoint context."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Mapping


class CheckpointError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckpointContext:
    checkpoint_id: str
    message: str | None
    agent: str | None
    date: str | None
    strategy: str | None
    session_count: int | None
    checkpoint_count: int | None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntireCheckpointClient:
    executable: str = "entire"
    timeout_seconds: float = 20.0

    def latest(self) -> CheckpointContext:
        records = self._json("checkpoint", "list", "--json")
        if not isinstance(records, list) or not records:
            raise CheckpointError("No Entire checkpoints are available for this branch.")
        first = records[0]
        if not isinstance(first, Mapping) or not isinstance(first.get("checkpoint_id"), str):
            raise CheckpointError("Entire returned checkpoint data in an unexpected format.")
        return self.get(first["checkpoint_id"], listing=first)

    def get(self, checkpoint_id: str, *, listing: Mapping[str, Any] | None = None) -> CheckpointContext:
        detail = self._json("checkpoint", "explain", checkpoint_id, "--json")
        if not isinstance(detail, Mapping):
            raise CheckpointError("Entire returned checkpoint detail in an unexpected format.")
        listed = listing or {}
        limitations = ["Checkpoint context describes recorded agent work; it does not by itself prove test execution or repository completeness."]
        if detail.get("strategy") != "manual-commit":
            limitations.append("Checkpoint strategy was not identified as manual-commit; inspect Entire output before relying on commit linkage.")
        return CheckpointContext(
            checkpoint_id=str(detail.get("checkpoint_id") or checkpoint_id),
            message=_text(listed.get("message")), agent=_text(listed.get("agent")), date=_text(listed.get("date")),
            strategy=_text(detail.get("strategy")), session_count=_integer(detail.get("session_count")),
            checkpoint_count=_integer(detail.get("checkpoints_count")), limitations=tuple(limitations),
        )

    def _json(self, *args: str) -> Any:
        try:
            result = subprocess.run([self.executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout_seconds, check=False)
        except FileNotFoundError as exc:
            raise CheckpointError(f"Entire checkpoint context is unavailable: executable not found: {self.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CheckpointError("Entire checkpoint context timed out.") from exc
        if result.returncode:
            raise CheckpointError(result.stderr.strip() or "Entire checkpoint context could not be queried.")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CheckpointError("Entire checkpoint context returned invalid JSON.") from exc


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
