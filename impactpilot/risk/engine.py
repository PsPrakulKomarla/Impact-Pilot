"""Transparent deterministic decision-support score; not a prediction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from impactpilot.change.diff import ChangedSymbol
from impactpilot.change.impact import ImpactFinding
from impactpilot.graph.evidence import EvidenceQuality


@dataclass(frozen=True)
class RiskFactor:
    signal: str
    value: int | str
    contribution: int
    reason: str
    source: str


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


def score_review(changes: Iterable[ChangedSymbol], findings: Iterable[ImpactFinding]) -> RiskResult:
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
    score = min(100, structural + verification)  # Historical (30%) is explicitly unavailable in Phase 4.
    level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH" if score < 80 else "CRITICAL"
    warnings = ("Historical evidence is unavailable in Phase 4; its 30-point component is not scored.",) if changes else ()
    return RiskResult(score, level, structural, 0, verification, "unavailable", tuple(factors), warnings)


def _factor(signal: str, value: int | str, contribution: int, reason: str, source: str) -> RiskFactor:
    return RiskFactor(signal, value, contribution, reason, source)
