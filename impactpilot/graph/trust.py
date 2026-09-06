"""Deterministic, conservative trust decisions over normalized Graph evidence."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import AnalysisStatus, Evidence, EvidenceQuality


# This list comes from `entire-graph capabilities --json`, not a confidence cutoff.
HEURISTIC_RELATION_TYPES = frozenset(
    {"HANDLES_ROUTE", "HTTP_CALLS", "EMITS", "LISTENS_ON", "HANDLES_TOOL", "SIMILAR_TO", "TESTS"}
)


@dataclass(frozen=True)
class TrustDecision:
    quality: EvidenceQuality
    verification_required: bool
    verification_reason: str | None
    recommended_action: str
    safe_for_downstream_structural_use: bool


def evaluate_evidence(evidence: Evidence) -> TrustDecision:
    """Classify explicit signals without interpreting numeric confidence ranges."""
    relationship = evidence.relationship
    if evidence.analysis_status in {AnalysisStatus.PARTIAL, AnalysisStatus.FAILED} or evidence.partial_failures:
        return _verification(EvidenceQuality.INCOMPLETE, "Entire Graph reported partial analysis or a partial failure.")
    if relationship.type in HEURISTIC_RELATION_TYPES:
        return _verification(EvidenceQuality.HEURISTIC, "Entire Graph identifies this relation family as heuristic.")
    if not relationship.type or not relationship.target or relationship.confidence is None or not relationship.resolution:
        return _verification(EvidenceQuality.UNKNOWN, "The Graph result lacks enough relationship metadata to establish evidence quality.")
    if evidence.analysis_status != AnalysisStatus.COMPLETE:
        return _verification(EvidenceQuality.UNKNOWN, "The Graph result does not explicitly establish complete analysis.")
    return TrustDecision(
        quality=EvidenceQuality.CONFIRMED,
        verification_required=False,
        verification_reason=None,
        recommended_action="Use as structural evidence; runtime behavior is still outside static analysis.",
        safe_for_downstream_structural_use=True,
    )


def _verification(quality: EvidenceQuality, reason: str) -> TrustDecision:
    return TrustDecision(
        quality=quality,
        verification_required=True,
        verification_reason=reason,
        recommended_action="Inspect the cited source location and run the relevant targeted test before relying on this finding.",
        safe_for_downstream_structural_use=False,
    )
