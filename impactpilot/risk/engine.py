"""Transparent deterministic decision-support score; not a prediction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from impactpilot.change.diff import ChangedSymbol
from impactpilot.change.impact import ImpactFinding
from impactpilot.graph.evidence import EvidenceQuality
from impactpilot.history.models import HistoricalEvidence


@dataclass(frozen=True)
class RiskFactor:
    signal: str
    value: int | str
    contribution: int
    reason: str
    source: str
    sample_size: int | None = None


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: str
    structural_component: int
    historical_component: int
    verification_component: int
    historical_status: str
    factors: tuple[RiskFactor, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {**asdict(self), "factors": [asdict(item) for item in self.factors]}


def score_review(changes: Iterable[ChangedSymbol], findings: Iterable[ImpactFinding], historical: HistoricalEvidence | None = None) -> RiskResult:
    changes, findings = tuple(changes), tuple(findings)
    factors: list[RiskFactor] = []
    structural = 0
    for change in changes:
        if change.signature_changed:
            structural += 18; factors.append(_factor("signature change", change.symbol, 18, "Signature contracts can affect callers.", "semantic diff"))
        elif change.body_changed:
            structural += 8; factors.append(_factor("body change", change.symbol, 8, "Implementation behavior changed.", "semantic diff"))
        elif change.deleted:
            structural += 15; factors.append(_factor("removed symbol", change.symbol, 15, "Removed symbols may leave callers unresolved.", "semantic diff"))
        elif change.renamed:
            structural += 12; factors.append(_factor("renamed symbol", change.symbol, 12, "Renames may require call-site updates.", "semantic diff"))
        if change.dependents_count:
            contribution = min(8, change.dependents_count)
            structural += contribution; factors.append(_factor("semantic dependents", change.dependents_count, contribution, "Provider-reported dependent count.", "semantic diff"))
    direct = sum(1 for item in findings if item.direct)
    transitive = sum(1 for item in findings if item.transitive)
    if direct:
        contribution = min(16, direct * 4); structural += contribution; factors.append(_factor("direct impact", direct, contribution, "Direct graph neighbors deserve first review.", "impact"))
    if transitive:
        contribution = min(8, transitive * 2); structural += contribution; factors.append(_factor("transitive impact", transitive, contribution, "Transitive callers may depend on changed behavior.", "impact"))
    structural = min(60, structural)
    uncertain = [item for item in findings if item.trust.quality != EvidenceQuality.CONFIRMED]
    verification = min(10, len(uncertain) * 5)
    if uncertain:
        factors.append(_factor("verification required", len(uncertain), verification, "Uncertain graph evidence must not be treated as absence of impact.", "trust layer"))
    historical_score = _historical_score(historical, factors)
    score = min(100, structural + historical_score + verification)
    level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH" if score < 80 else "CRITICAL"
    historical_status = "available" if historical and historical.available else "unavailable"
    warnings = tuple(historical.limitations) if historical else ("Historical evidence is unavailable; its 30-point component is not scored.",)
    return RiskResult(score, level, structural, historical_score, verification, historical_status, tuple(factors), warnings)


def _historical_score(evidence: HistoricalEvidence | None, factors: list[RiskFactor]) -> int:
    if not evidence or not evidence.available or evidence.sample_size == 0:
        return 0
    # Proposed ImpactPilot policy: one event is visible but cannot establish a pattern.
    if evidence.sample_size == 1:
        factors.append(_factor("historical sample", 1, 0, "One related event is limited evidence, not a pattern.", evidence.source, 1))
        return 0
    recurrence = min(10, (evidence.sample_size - 1) * 3)
    impacts = min(8, len(evidence.impact_patterns) * 2)
    failures = min(12, len(evidence.failed_tests) * 6)
    if recurrence: factors.append(_factor("historical change recurrence", evidence.sample_size, recurrence, "Related changes were observed in the bounded historical window.", evidence.source, evidence.sample_size))
    if impacts: factors.append(_factor("historical impact recurrence", len(evidence.impact_patterns), impacts, "Related Graph impact snapshots were observed; their trust state remains attached.", evidence.source, evidence.sample_size))
    if failures: factors.append(_factor("historical test failures", len(evidence.failed_tests), failures, "Historical records associate related changes with test failures; this does not predict this change.", evidence.source, evidence.sample_size))
    return min(30, recurrence + impacts + failures)


def _factor(signal: str, value: int | str, contribution: int, reason: str, source: str, sample_size: int | None = None) -> RiskFactor:
    return RiskFactor(signal, value, contribution, reason, source, sample_size)
