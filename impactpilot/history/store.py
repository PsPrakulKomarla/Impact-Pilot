"""Local test store; never labels its data as production Databricks evidence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from .models import ChangeEvent, HistoricalEvidence, ImpactSnapshot, TestEvent


class HistoricalStore(ABC):
    @abstractmethod
    def ingest(self, changes: Iterable[ChangeEvent], tests: Iterable[TestEvent], impacts: Iterable[ImpactSnapshot]) -> None: ...

    @abstractmethod
    def lookup(self, repository: str, symbols: Iterable[str], files: Iterable[str]) -> HistoricalEvidence: ...


@dataclass
class InMemoryHistoricalStore(HistoricalStore):
    """Idempotent deterministic test adapter; its caller supplies explicit data_kind."""
    changes: dict[str, ChangeEvent] = field(default_factory=dict)
    tests: dict[str, TestEvent] = field(default_factory=dict)
    impacts: dict[str, ImpactSnapshot] = field(default_factory=dict)

    def ingest(self, changes, tests, impacts) -> None:
        self.changes.update({item.event_id: item for item in changes})
        self.tests.update({item.event_id: item for item in tests})
        self.impacts.update({item.snapshot_id: item for item in impacts})

    def lookup(self, repository, symbols, files) -> HistoricalEvidence:
        symbols, files = set(symbols), set(files)
        changes = tuple(item for item in self.changes.values() if item.repository == repository and (symbols.intersection(item.changed_symbols) or files.intersection(item.changed_files)))
        commits = {item.commit for item in changes}
        impacts = tuple(item for item in self.impacts.values() if item.repository == repository and item.symbol in symbols)
        tests = tuple(item for item in self.tests.values() if item.repository == repository and item.commit in commits)
        sample_size = len(changes)
        if not sample_size and not impacts:
            return HistoricalEvidence(False, "in_memory", None, 0, limitations=("No relevant historical records were found.",))
        kinds = {item.data_kind for item in (*changes, *tests, *impacts)}
        kind = next(iter(kinds)) if len(kinds) == 1 else "REPRESENTATIVE"
        limits = ("Limited historical evidence; one related change event.",) if sample_size == 1 else ()
        return HistoricalEvidence(True, "in_memory", kind, sample_size, changes, tests, impacts, limits)
