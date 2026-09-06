"""Evidence-backed next actions for a change review."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from impactpilot.change.impact import ImpactFinding


@dataclass(frozen=True)
class Recommendation:
    priority: int
    action: str
    reason: str
    evidence_source: str


@dataclass(frozen=True)
class VerificationPlan:
    required: bool
    source_checks: tuple[str, ...]
    test_checks: tuple[str, ...]
    graph_checks: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def recommend(findings: Iterable[ImpactFinding]) -> tuple[tuple[Recommendation, ...], VerificationPlan]:
    findings = tuple(findings)
    recommendations: list[Recommendation] = []
    source_checks: list[str] = []
    reasons: list[str] = []
    for finding in findings:
        qualifier = "direct" if finding.direct else "transitive" if finding.transitive else "reported"
        location = finding.evidence.relationship.evidence[0] if finding.evidence.relationship.evidence else None
        location_text = f" at {location.file}:{location.line}" if location and location.file and location.line else ""
        if finding.direct:
            recommendations.append(Recommendation(1, f"Review direct {finding.category}: {finding.impacted_symbol}.", f"Entire Graph impact reports a direct {finding.relationship or 'relationship'}.", finding.evidence.provenance.command))
        elif finding.transitive:
            recommendations.append(Recommendation(4, f"Verify transitive impact on {finding.impacted_symbol}.", "Impact is transitive, so behavior should be confirmed through its direct path.", finding.evidence.provenance.command))
        if finding.trust.verification_required:
            recommendations.append(Recommendation(2, f"Inspect {finding.impacted_symbol}{location_text}.", finding.trust.verification_reason or "Graph evidence needs verification.", finding.evidence.provenance.command))
            source_checks.append(f"Inspect {finding.impacted_symbol}{location_text} ({qualifier} {finding.category}).")
            reasons.append(finding.trust.verification_reason or "Graph evidence is uncertain.")
    recommendations.sort(key=lambda item: (item.priority, item.action))
    unique = tuple(dict.fromkeys(recommendations))
    plan = VerificationPlan(
        required=bool(reasons),
        source_checks=tuple(dict.fromkeys(source_checks)),
        test_checks=(),  # No test name is guessed without Graph/source evidence.
        graph_checks=tuple(f"Re-check impact of {item.changed_symbol}." for item in findings if item.trust.verification_required),
        reasons=tuple(dict.fromkeys(reasons)),
    )
    return unique, plan
