from __future__ import annotations

import json
import unittest
from pathlib import Path

from impactpilot.graph.evidence import AnalysisStatus, EvidenceQuality, normalize_graph_output
from impactpilot.graph.trust import evaluate_evidence


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class EvidenceContractTests(unittest.TestCase):
    def test_fully_resolved_relationship_is_confirmed_structural_evidence(self) -> None:
        evidence = normalize_graph_output(load("fully_resolved_graph.json"), command="neighbors")[0]
        decision = evaluate_evidence(evidence)

        self.assertEqual(evidence.analysis_status, AnalysisStatus.COMPLETE)
        self.assertEqual(evidence.relationship.confidence, 0.92)
        self.assertEqual(evidence.relationship.resolution, "exact")
        self.assertEqual(evidence.relationship.evidence[0].file, "checkout.py")
        self.assertEqual(evidence.relationship.evidence[0].line, 18)
        self.assertEqual(decision.quality, EvidenceQuality.CONFIRMED)
        self.assertFalse(decision.verification_required)
        self.assertTrue(decision.safe_for_downstream_structural_use)

    def test_heuristic_relation_requires_verification_without_a_confidence_threshold(self) -> None:
        evidence = normalize_graph_output(load("heuristic_graph.json"), command="neighbors")[0]
        decision = evaluate_evidence(evidence)

        self.assertEqual(decision.quality, EvidenceQuality.HEURISTIC)
        self.assertTrue(decision.verification_required)
        self.assertIn("heuristic", decision.verification_reason.lower())

    def test_partial_analysis_is_not_presented_as_confirmed(self) -> None:
        evidence = normalize_graph_output(load("partial_graph.json"), command="impact")[0]
        decision = evaluate_evidence(evidence)

        self.assertEqual(evidence.analysis_status, AnalysisStatus.PARTIAL)
        self.assertEqual(evidence.partial_failures[0]["code"], "E_PARSE_DEPTH_EXCEEDED")
        self.assertIn("E_PARSE_DEPTH_EXCEEDED", evidence.warnings[0])
        self.assertEqual(decision.quality, EvidenceQuality.INCOMPLETE)
        self.assertTrue(decision.verification_required)
        self.assertFalse(decision.safe_for_downstream_structural_use)
        self.assertIn("Inspect", decision.recommended_action)

    def test_warning_without_documented_coverage_signal_stays_unknown(self) -> None:
        payload = {
            "warnings": ["result limited by an output budget"],
            "relations": [{"type": "CALLS", "to": "target", "confidence": 0.92, "resolution": "exact"}],
        }
        evidence = normalize_graph_output(payload, command="neighbors")[0]
        decision = evaluate_evidence(evidence)

        self.assertEqual(evidence.analysis_status, AnalysisStatus.UNKNOWN)
        self.assertEqual(decision.quality, EvidenceQuality.UNKNOWN)
        self.assertTrue(decision.verification_required)

    def test_missing_relationship_metadata_is_unknown_and_traceable(self) -> None:
        payload = {"relations": [{"type": "CALLS", "evidence": [{"file": "x.py", "line": 4}]}]}
        evidence = normalize_graph_output(payload, command="neighbors")[0]
        decision = evaluate_evidence(evidence)

        self.assertEqual(decision.quality, EvidenceQuality.UNKNOWN)
        self.assertEqual(evidence.audit_record()["relationship"]["evidence"][0]["file"], "x.py")

    def test_unknown_command_shape_is_retained_as_unknown_evidence(self) -> None:
        evidence = normalize_graph_output({"unexpected": True}, command="diff")[0]
        self.assertEqual(evidence.analysis_status, AnalysisStatus.UNKNOWN)
        self.assertEqual(evaluate_evidence(evidence).quality, EvidenceQuality.UNKNOWN)
        self.assertTrue(evidence.raw["unexpected"])

    def test_actual_neighbors_shape_is_flattened_with_endpoint_and_call_site(self) -> None:
        payload = {
            "repo_root": "fixture/complete",
            "stats": {"completeness_level": "ok"},
            "matches": [
                {
                    "symbol": {"name": "charge", "kind": "function", "file_path": "payment.py", "start_line": 4},
                    "incoming": [
                        {
                            "relation": "CALLS",
                            "endpoint": {"name": "place_order", "file_path": "checkout.py", "start_line": 18},
                            "confidence": 0.92,
                            "resolution": "exact",
                            "reason": "same-file declaration",
                            "evidence": [{"file_path": "checkout.py", "start_line": 18}],
                        }
                    ],
                    "outgoing": [],
                }
            ],
        }
        evidence = normalize_graph_output(payload, command="neighbors")[0]
        self.assertEqual(evidence.subject, "charge")
        self.assertEqual(evidence.relationship.target, "place_order")
        self.assertEqual(evidence.relationship.direction, "incoming")
        self.assertEqual(evidence.relationship.evidence[0].line, 18)
        self.assertEqual(evaluate_evidence(evidence).quality, EvidenceQuality.CONFIRMED)

    def test_explicitly_truncated_neighbors_response_is_partial(self) -> None:
        payload = load("fully_resolved_graph.json") | {"truncated": True}
        evidence = normalize_graph_output(payload, command="neighbors")[0]
        self.assertEqual(evidence.analysis_status, AnalysisStatus.PARTIAL)
        self.assertEqual(evaluate_evidence(evidence).quality, EvidenceQuality.INCOMPLETE)
