"""Small subprocess adapter for the existing Entire Graph CLI."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GraphClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphClient:
    executable: str = "entire-graph"
    timeout_seconds: float = 120.0

    def run_json(self, command: str, repository: Path, *args: str) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [self.executable, command, "--repo", str(repository), *args],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GraphClientError(f"Entire Graph executable is unavailable: {self.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise GraphClientError(f"Entire Graph {command} timed out after {self.timeout_seconds:g}s") from exc
        if completed.returncode:
            raise GraphClientError(completed.stderr.strip() or f"Entire Graph {command} failed with exit code {completed.returncode}")
        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise GraphClientError(f"Entire Graph {command} returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise GraphClientError(f"Entire Graph {command} returned a JSON value, not an object")
        return data
