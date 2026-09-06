"""Bounded commit-to-commit ImpactPilot review workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from impactpilot.graph.client import GraphClient, GraphClientError
from impactpilot.history.models import HistoricalEvidence
from impactpilot.history.store import HistoricalStore
from impactpilot.recommendations.engine import Recommendation, VerificationPlan, recommend
from impactpilot.risk.engine import RiskResult, score_review

from .diff import ChangedSymbol, normalize_diff
from .impact import ImpactFinding, analyze_impact


@dataclass(frozen=True)
class ChangeReview:
    baseline: str
    target: str
    status: str
    changes: tuple[ChangedSymbol, ...]
    impact: tuple[ImpactFinding, ...]
    risk: RiskResult | None
    recommendations: tuple[Recommendation, ...]
    verification: VerificationPlan | None
    historical: HistoricalEvidence | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "review": {"baseline": self.baseline, "target": self.target, "status": self.status},
            "changes": [asdict(item) for item in self.changes],
            "impact": [_finding_dict(item) for item in self.impact],
            "risk": self.risk.to_dict() if self.risk else None,
            "recommendations": [asdict(item) for item in self.recommendations],
            "verification": self.verification.to_dict() if self.verification else None,
            "historical": self.historical.to_dict() if self.historical else None,
            "warnings": list(self.warnings),
        }


class ReviewService:
    """Uses one commit/ref semantic diff; it never claims worktree-vs-HEAD diff support."""

    def __init__(self, client: GraphClient, *, historical_store: HistoricalStore | None = None, max_symbols: int = 20) -> None:
        self.client, self.historical_store, self.max_symbols = client, historical_store, max_symbols

    def review(self, repository: Path, *, base: str, head: str) -> ChangeReview:
        try:
            diff = self.client.run_json("diff", repository, "--base", base, "--head", head, "--json")
        except GraphClientError as exc:
            return ChangeReview(base, head, "failed", (), (), None, (), None, None, (str(exc),))
        changes = normalize_diff(diff)
        warnings = tuple(_warning(item) for item in diff.get("warnings", ()) if isinstance(item, Mapping))
        if not changes:
            return ChangeReview(base, head, "no_semantic_changes", (), (), score_review((), ()), (), recommend(())[1], None, warnings)
        selected = changes[: self.max_symbols]
        if len(changes) > len(selected):
            warnings += (f"Review limited to {self.max_symbols} changed symbols; remaining symbols require verification.",)
        findings: list[ImpactFinding] = []
        for change in selected:
            if change.deleted:
                warnings += (f"Removed symbol {change.symbol} cannot be queried with impact; inspect prior callers manually.",)
                continue
            try:
                impact = self.client.run_json("impact", repository, "--symbol", change.symbol, "--file", change.file, "--format", "json")
                neighbors = self.client.run_json("neighbors", repository, "--symbol", change.symbol, "--file", change.file, "--format", "json")
                findings.extend(analyze_impact(change, impact, neighbors))
            except GraphClientError as exc:
                warnings += (f"Impact unavailable for {change.symbol}: {exc}",)
        historical = self._history(repository, selected)
        risk = score_review(selected, findings, historical)
        recommendations, verification = recommend(findings, historical)
        return ChangeReview(base, head, "complete", selected, tuple(findings), risk, recommendations, verification, historical, warnings + risk.warnings)

    def _history(self, repository: Path, changes: tuple[ChangedSymbol, ...]) -> HistoricalEvidence | None:
        if not self.historical_store:
            return None
        try:
            return self.historical_store.lookup(str(repository), (item.symbol for item in changes), (item.file for item in changes))
        except Exception as exc:
            return HistoricalEvidence(False, "historical_store", None, 0, limitations=(f"Historical intelligence unavailable: {exc}",))


def _warning(item: Mapping[str, Any]) -> str:
    return str(item.get("code") or item.get("message") or dict(item))


def _finding_dict(finding: ImpactFinding) -> dict[str, Any]:
    return {
        "changed_symbol": finding.changed_symbol,
        "impacted_symbol": finding.impacted_symbol,
        "relationship": finding.relationship,
        "category": finding.category,
        "direct": finding.direct,
        "transitive": finding.transitive,
        "trust": asdict(finding.trust) | {"quality": finding.trust.quality.value},
        "evidence": finding.evidence.audit_record(),
    }
