"""Small, provenance-first historical records used by change reviews."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


DataKind = Literal["REAL", "SYNTHETIC", "REPRESENTATIVE"]


@dataclass(frozen=True)
class ChangeEvent:
    event_id: str
    repository: str
    commit: str
    parent_commit: str | None
    captured_at: str
    changed_files: tuple[str, ...]
    changed_symbols: tuple[str, ...]
    change_types: tuple[str, ...]
    data_kind: DataKind
    source: str


@dataclass(frozen=True)
class TestEvent:
    event_id: str
    repository: str
    commit: str
    captured_at: str
    test_command: str
    test_scope: str
    result: Literal["PASS", "FAIL", "ERROR", "SKIPPED", "UNAVAILABLE"]
    duration_ms: int | None
    failure_summary: str | None
    data_kind: DataKind
    source: str


@dataclass(frozen=True)
class ImpactSnapshot:
    snapshot_id: str
    repository: str
    commit: str
    symbol: str
    impacted_symbol: str
    relationship: str | None
    confidence: float | None
    resolution: str | None
    trust_classification: str
    source_file: str | None
    source_line: int | None
    captured_at: str
    data_kind: DataKind
    source: str


@dataclass(frozen=True)
class HistoricalEvidence:
    available: bool
    source: str
    data_kind: DataKind | None
    sample_size: int
    related_change_events: tuple[ChangeEvent, ...] = ()
    related_test_events: tuple[TestEvent, ...] = ()
    impact_patterns: tuple[ImpactSnapshot, ...] = ()
    limitations: tuple[str, ...] = ()

    @property
    def failed_tests(self) -> tuple[TestEvent, ...]:
        return tuple(event for event in self.related_test_events if event.result == "FAIL")

    def to_dict(self) -> dict:
        return asdict(self)
