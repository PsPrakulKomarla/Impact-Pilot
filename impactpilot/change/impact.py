"""Impact response interpretation, always gated through Phase 3 trust."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from impactpilot.graph.evidence import Evidence, Location, Provenance, Relationship, analysis_status, normalize_graph_output
from impactpilot.graph.trust import TrustDecision, evaluate_evidence

from .diff import ChangedSymbol


@dataclass(frozen=True)
class ImpactFinding:
    changed_symbol: str
    impacted_symbol: str
    relationship: str | None
    category: str
    direct: bool
    transitive: bool
    evidence: Evidence
    trust: TrustDecision


def analyze_impact(
    changed: ChangedSymbol, impact_payload: Mapping[str, Any], neighbors_payload: Mapping[str, Any]
) -> tuple[ImpactFinding, ...]:
    """Join bounded impact sections with relation metadata from neighbors.

    `impact` supplies the direct/transitive shape, while `neighbors` supplies
    confidence/resolution/reason/evidence needed by the trust gate.
    """
    neighbor_evidence = normalize_graph_output(neighbors_payload, command="neighbors")
    by_target = {item.relationship.target: item for item in neighbor_evidence if item.relationship.target}
    findings: list[ImpactFinding] = []
    sections = (("callers", "caller"), ("callees", "dependency"), ("type_consumers", "type"), ("data_flows", "data_flow"))
    for section_name, category in sections:
        section = impact_payload.get(section_name)
        if not isinstance(section, Mapping):
            continue
        for entry in section.get("entries", ()):
            if not isinstance(entry, Mapping):
                continue
            endpoint = entry.get("endpoint")
            if not isinstance(endpoint, Mapping):
                continue
            name = endpoint.get("qualified_name") or endpoint.get("name") or endpoint.get("id")
            if not isinstance(name, str):
                continue
            evidence = by_target.get(name) or _unresolved_impact_evidence(changed, name, entry, impact_payload)
            trust = evaluate_evidence(evidence)
            depth = entry.get("depth")
            findings.append(
                ImpactFinding(
                    changed_symbol=changed.symbol,
                    impacted_symbol=name,
                    relationship=entry.get("relation") if isinstance(entry.get("relation"), str) else evidence.relationship.type,
                    category=category,
                    direct=depth == 1,
                    transitive=isinstance(depth, int) and depth > 1,
                    evidence=evidence,
                    trust=trust,
                )
            )
    return tuple(findings)


def _unresolved_impact_evidence(
    changed: ChangedSymbol, target: str, entry: Mapping[str, Any], payload: Mapping[str, Any]
) -> Evidence:
    endpoint = entry.get("endpoint") if isinstance(entry.get("endpoint"), Mapping) else {}
    call_site = entry.get("call_site") if isinstance(entry.get("call_site"), Mapping) else endpoint
    return Evidence(
        provenance=Provenance(command="impact", repository=payload.get("repo_root") if isinstance(payload.get("repo_root"), str) else None),
        subject=changed.symbol,
        subject_kind=changed.kind,
        subject_location=Location(changed.file, changed.line),
        relationship=Relationship(
            type=entry.get("relation") if isinstance(entry.get("relation"), str) else None,
            target=target,
            direction=entry.get("direction") if isinstance(entry.get("direction"), str) else None,
            evidence=(Location(call_site.get("file_path"), call_site.get("line")),),
        ),
        analysis_status=analysis_status(payload),
        warnings=tuple(str(item) for item in payload.get("warnings", ()) if isinstance(item, str)),
        partial_failures=tuple(item for item in payload.get("partial_failures", ()) if isinstance(item, Mapping)),
        raw=entry,
    )
