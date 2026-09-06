"""Normalization for the public Entire Graph JSON contract.

This module deliberately preserves provider values.  It does not assign meaning
to a numeric confidence score: Entire Graph's confidence is evidence, not a
runtime guarantee.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class EvidenceQuality(str, Enum):
    CONFIRMED = "confirmed"
    HEURISTIC = "heuristic"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


class AnalysisStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    FAILED = "failed"


@dataclass(frozen=True)
class Location:
    file: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class Relationship:
    type: str | None = None
    target: str | None = None
    direction: str | None = None
    confidence: float | None = None
    resolution: str | None = None
    reason: str | None = None
    evidence: tuple[Location, ...] = ()
    guards: tuple[str, ...] = ()


@dataclass(frozen=True)
class Provenance:
    tool: str = "entire-graph"
    command: str = "unknown"
    repository: str | None = None
    ref: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class Evidence:
    """One traceable graph finding plus its result-level context."""

    provenance: Provenance
    subject: str | None = None
    subject_kind: str | None = None
    subject_location: Location = field(default_factory=Location)
    relationship: Relationship = field(default_factory=Relationship)
    analysis_status: AnalysisStatus = AnalysisStatus.UNKNOWN
    warnings: tuple[str, ...] = ()
    partial_failures: tuple[Mapping[str, Any], ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def audit_record(self) -> dict[str, Any]:
        """Return a JSON-ready, compact explanation without discarding raw proof."""
        result = asdict(self)
        result["analysis_status"] = self.analysis_status.value
        result["raw"] = dict(self.raw)
        return result


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Iterable[Any]:
    return value if isinstance(value, list) else ()


def _location(value: Any) -> Location:
    item = _as_mapping(value)
    return Location(
        file=_text(item.get("file") or item.get("path") or item.get("file_path")),
        line=_integer(item.get("line") or item.get("start_line")),
    )


def _locations(value: Any) -> tuple[Location, ...]:
    if isinstance(value, Mapping):
        return (_location(value),)
    return tuple(_location(item) for item in _as_sequence(value))


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def analysis_status(result: Mapping[str, Any]) -> AnalysisStatus:
    """Use only explicit result-level coverage signals; never infer completeness."""
    partial_failures = result.get("partial_failures")
    warnings = result.get("warnings")
    stats = _as_mapping(result.get("stats"))
    level = _text(result.get("completeness_level")) or _text(stats.get("completeness_level"))
    completeness = _as_mapping(result.get("completeness"))
    level = level or _text(completeness.get("level"))

    if result.get("truncated") or result.get("focus_matches_truncated"):
        return AnalysisStatus.PARTIAL
    if partial_failures or level in {"degraded", "partial", "failed"}:
        return AnalysisStatus.PARTIAL
    if level in {"ok", "complete"}:
        return AnalysisStatus.COMPLETE
    # Warnings alone are retained but vary in severity; do not manufacture partiality.
    if warnings:
        return AnalysisStatus.UNKNOWN
    return AnalysisStatus.UNKNOWN


def _warning_text(value: Any) -> str:
    item = _as_mapping(value)
    if item:
        return _text(item.get("code")) or _text(item.get("message")) or str(dict(item))
    return str(value)


def _neighbor_records(root: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Flatten the documented neighbors `matches[].incoming/outgoing` shape."""
    records: list[Mapping[str, Any]] = []
    for match_value in _as_sequence(root.get("matches")):
        match = _as_mapping(match_value)
        subject = _as_mapping(match.get("symbol"))
        for direction in ("incoming", "outgoing"):
            for edge_value in _as_sequence(match.get(direction)):
                edge = dict(_as_mapping(edge_value))
                endpoint = _as_mapping(edge.get("endpoint"))
                edge["from"] = subject.get("qualified_name") or subject.get("name")
                edge["from_kind"] = subject.get("kind")
                edge["from_location"] = subject
                edge["to"] = endpoint.get("qualified_name") or endpoint.get("name") or endpoint.get("id")
                edge["source"] = endpoint
                edge["direction"] = edge.get("direction") or direction
                records.append(edge)
    return tuple(records)


def normalize_graph_output(
    payload: Mapping[str, Any], *, command: str, repository: str | None = None
) -> list[Evidence]:
    """Normalize relation-shaped JSON from neighbors, impact, or snapshot output.

    Unknown command shapes produce one UNKNOWN evidence record.  This is safer
    than silently throwing raw output away or claiming it was fully analyzed.
    """
    root = _as_mapping(payload)
    provenance = Provenance(
        command=command,
        repository=repository or _text(root.get("repository")),
        ref=_text(root.get("ref")) or _text(root.get("commit")) or _text(root.get("tree")),
        version=_text(root.get("provider_version")) or _text(root.get("version")),
    )
    status = analysis_status(root)
    warnings = tuple(_warning_text(item) for item in _as_sequence(root.get("warnings")))
    failures = tuple(_as_mapping(item) for item in _as_sequence(root.get("partial_failures")))
    records = _as_sequence(root.get("relations")) or _as_sequence(root.get("findings")) or _neighbor_records(root)
    if not records and root.get("record_type") == "relation":
        records = (root,)
    if not records:
        return [Evidence(provenance, analysis_status=status, warnings=warnings, partial_failures=failures, raw=root)]

    normalized: list[Evidence] = []
    for record_value in records:
        record = _as_mapping(record_value)
        evidence = _locations(record.get("evidence") or record.get("call_site"))
        normalized.append(
            Evidence(
                provenance=provenance,
                subject=_text(record.get("from")) or _text(record.get("from_id")),
                subject_kind=_text(record.get("from_kind")),
                subject_location=_location(record.get("source") or record.get("from_location")),
                relationship=Relationship(
                    type=_text(record.get("type")) or _text(record.get("relation")),
                    target=_text(record.get("to")) or _text(record.get("to_id")) or _text(record.get("endpoint")),
                    direction=_text(record.get("direction")),
                    confidence=_number(record.get("confidence")),
                    resolution=_text(record.get("resolution")),
                    reason=_text(record.get("reason")),
                    evidence=evidence,
                    guards=tuple(str(item) for item in _as_sequence(record.get("guards"))),
                ),
                analysis_status=status,
                warnings=warnings + tuple(_warning_text(item) for item in _as_sequence(record.get("warnings"))),
                partial_failures=failures,
                raw=record,
            )
        )
    return normalized
