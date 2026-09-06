from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from impactpilot.change.review import ReviewService
from impactpilot.change.diff import ChangedSymbol
from impactpilot.__main__ import _render
from impactpilot.graph.client import GraphClientError
from impactpilot.history.models import ChangeEvent, HistoricalEvidence, TestEvent
from impactpilot.risk.engine import score_review


def diff(*changes):
    return {"files": [{"path": "service.py", "changes": list(changes)}]}


def change(name="authenticate", type="body_changed", **extra):
    return {"name": name, "kind": "function", "type": type, "after_start_line": 10, "dependents_count": 0, **extra}


def impact(*entries, partial=False):
    return {
        "stats": {"completeness_level": "degraded" if partial else "ok"},
        "partial_failures": [{"code": "E_PARSE_ERROR"}] if partial else [],
        "callers": {"entries": list(entries)},
        "callees": {"entries": []}, "type_consumers": {"entries": []}, "data_flows": {"entries": []},
    }


def neighbor(target="LoginHandler", relation="CALLS", *, partial=False):
    return {
        "stats": {"completeness_level": "degraded" if partial else "ok"},
        "partial_failures": [{"code": "E_PARSE_ERROR"}] if partial else [],
        "matches": [{"symbol": {"name": "authenticate", "kind": "function", "file_path": "service.py", "start_line": 10}, "incoming": [{"direction": "in", "relation": relation, "endpoint": {"name": target, "file_path": "routes.py", "start_line": 8}, "confidence": 0.9, "resolution": "exact", "reason": "fixture", "evidence": [{"file_path": "routes.py", "start_line": 8}]}], "outgoing": []}],
    }


class FakeGraph:
    def __init__(self, diff_payload, impact_payload=None, neighbor_payload=None):
        self.payloads = {"diff": diff_payload, "impact": impact_payload or impact(), "neighbors": neighbor_payload or neighbor()}

    def run_json(self, command, repository, *args):
        value = self.payloads[command]
        if isinstance(value, Exception):
            raise value
        return value


class ChangeReviewTests(unittest.TestCase):
    def review(self, diff_payload, impact_payload=None, neighbor_payload=None):
        return ReviewService(FakeGraph(diff_payload, impact_payload, neighbor_payload)).review(Path("."), base="base", head="head")

    def test_body_change_runs_end_to_end_with_direct_impact_and_recommendation(self):
        item = {"endpoint": {"name": "LoginHandler", "file_path": "routes.py", "start_line": 8}, "relation": "CALLS", "direction": "in", "depth": 1, "call_site": {"file_path": "routes.py", "line": 8}}
        result = self.review(diff(change()), impact(item), neighbor())
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.impact[0].trust.quality.value, "confirmed")
        self.assertTrue(result.impact[0].direct)
        self.assertGreater(result.risk.score, 0)
        self.assertIn("Review direct", result.recommendations[0].action)
        self.assertEqual(result.risk.historical_status, "unavailable")

    def test_signature_change_is_a_larger_explicit_risk_factor(self):
        body = self.review(diff(change(type="body_changed")))
        signature = self.review(diff(change(type="signature_changed")))
        self.assertGreater(signature.risk.score, body.risk.score)
        self.assertTrue(any(f.signal == "signature change" for f in signature.risk.factors))

    def test_transitive_impact_is_distinguished(self):
        item = {"endpoint": {"name": "Dashboard", "file_path": "dashboard.py", "start_line": 5}, "relation": "CALLS", "direction": "in", "depth": 2}
        result = self.review(diff(change()), impact(item), neighbor("Dashboard"))
        self.assertTrue(result.impact[0].transitive)
        self.assertFalse(result.impact[0].direct)
        self.assertIn("transitive", result.recommendations[0].action)

    def test_no_impact_is_not_artificially_high_risk(self):
        result = self.review(diff(change()))
        self.assertEqual(result.risk.level, "LOW")
        self.assertEqual(result.impact, ())

    def test_heuristic_relation_propagates_to_risk_and_verification(self):
        item = {"endpoint": {"name": "POST /login"}, "relation": "HANDLES_ROUTE", "depth": 1}
        result = self.review(diff(change()), impact(item), neighbor("POST /login", "HANDLES_ROUTE"))
        self.assertEqual(result.impact[0].trust.quality.value, "heuristic")
        self.assertTrue(result.verification.required)
        self.assertEqual(result.risk.verification_component, 5)

    def test_partial_analysis_is_never_promoted_to_confirmed(self):
        item = {"endpoint": {"name": "LoginHandler"}, "relation": "CALLS", "depth": 1}
        result = self.review(diff(change()), impact(item, partial=True), neighbor(partial=True))
        self.assertEqual(result.impact[0].trust.quality.value, "incomplete")
        self.assertTrue(result.verification.required)

    def test_deleted_symbol_does_not_issue_an_impact_query(self):
        result = self.review(diff(change(type="removed")))
        self.assertEqual(result.impact, ())
        self.assertTrue(any("Removed symbol" in warning for warning in result.warnings))

    def test_renamed_symbol_is_handled_and_bounded_large_reviews_are_disclosed(self):
        changes = [change(name=f"f{i}", type="renamed") for i in range(22)]
        result = ReviewService(FakeGraph(diff(*changes)), max_symbols=20).review(Path("."), base="base", head="head")
        self.assertEqual(len(result.changes), 20)
        self.assertTrue(any("limited" in warning for warning in result.warnings))

    def test_graph_failure_is_not_a_successful_review(self):
        result = ReviewService(FakeGraph(GraphClientError("Graph CLI missing"))).review(Path("."), base="base", head="head")
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.risk)

    def test_historical_store_failure_keeps_graph_review_running(self):
        class FailingHistory:
            def lookup(self, *args): raise RuntimeError("Databricks unavailable")
        result = ReviewService(FakeGraph(diff(change())), historical_store=FailingHistory()).review(Path("."), base="base", head="head")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.risk.historical_status, "unavailable")
        self.assertIn("Historical intelligence unavailable", result.historical.limitations[0])

    def test_historical_failed_test_changes_recommendation_and_risk(self):
        class History:
            def lookup(self, *args):
                event = ChangeEvent("c", ".", "commit", None, "now", ("service.py",), ("authenticate",), ("body_changed",), "SYNTHETIC", "fixture")
                failed = TestEvent("t", ".", "commit", "now", "python -m unittest auth", "authentication", "FAIL", 1, "failure", "SYNTHETIC", "fixture")
                return HistoricalEvidence(True, "fixture", "SYNTHETIC", 2, (event, event), (failed,), ())
        result = ReviewService(FakeGraph(diff(change())), historical_store=History()).review(Path("."), base="base", head="head")
        self.assertGreater(result.risk.historical_component, 0)
        self.assertIn("python -m unittest auth", result.verification.test_checks)

    def test_human_output_is_windows_console_safe(self):
        result = self.review(diff())
        output = StringIO()
        with redirect_stdout(output):
            _render(result)
        self.assertIn("Baseline: base -> head", output.getvalue())
        self.assertIn("Risk: LOW - 0/100", output.getvalue())

    def test_risk_components_are_bounded_and_sum_to_total(self):
        changes = tuple(ChangedSymbol(f"s{index}", "function", "service.py", 1, "signature_changed", 99, None, None, {}) for index in range(10))
        result = score_review(changes, ())
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)
        self.assertLessEqual(result.structural_component, 60)
        self.assertLessEqual(result.historical_component, 30)
        self.assertLessEqual(result.verification_component, 10)
        self.assertEqual(result.score, result.structural_component + result.historical_component + result.verification_component)
