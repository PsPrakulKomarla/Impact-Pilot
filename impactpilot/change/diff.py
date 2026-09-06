"""Normalize Entire Graph's documented `diff --json` response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ChangedSymbol:
    symbol: str
    kind: str | None
    file: str
    line: int | None
    change_type: str
    dependents_count: int
    old_signature: str | None
    new_signature: str | None
    raw: Mapping[str, Any]

    @property
    def signature_changed(self) -> bool:
        return self.change_type == "signature_changed"

    @property
    def body_changed(self) -> bool:
        return self.change_type == "body_changed"

    @property
    def deleted(self) -> bool:
        return self.change_type == "removed"

    @property
    def renamed(self) -> bool:
        return self.change_type == "renamed"


def normalize_diff(payload: Mapping[str, Any]) -> tuple[ChangedSymbol, ...]:
    """Preserve provider records; skip only malformed records with no name."""
    changes: list[ChangedSymbol] = []
    files = payload.get("files")
    if not isinstance(files, list):
        return ()
    for file_record in files:
        if not isinstance(file_record, Mapping):
            continue
        path = file_record.get("path")
        if not isinstance(path, str):
            continue
        for item in file_record.get("changes", ()):
            if not isinstance(item, Mapping):
                continue
            name = item.get("name") or item.get("old_name") or item.get("new_name")
            change_type = item.get("type")
            if not isinstance(name, str) or not isinstance(change_type, str):
                continue
            count = item.get("dependents_count")
            changes.append(
                ChangedSymbol(
                    symbol=name,
                    kind=item.get("kind") if isinstance(item.get("kind"), str) else None,
                    file=path,
                    line=_line(item),
                    change_type=change_type,
                    dependents_count=count if isinstance(count, int) and count >= 0 else 0,
                    old_signature=item.get("old_signature") if isinstance(item.get("old_signature"), str) else None,
                    new_signature=item.get("new_signature") if isinstance(item.get("new_signature"), str) else None,
                    raw=item,
                )
            )
    return tuple(changes)


def _line(item: Mapping[str, Any]) -> int | None:
    for field in ("after_start_line", "before_start_line"):
        value = item.get(field)
        if isinstance(value, int):
            return value
    return None
