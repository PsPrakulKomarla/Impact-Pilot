from __future__ import annotations

import unittest

from impactpilot.history.models import ChangeEvent, ImpactSnapshot, TestEvent
from impactpilot.history.store import InMemoryHistoricalStore
from impactpilot.risk.engine import score_review
from impactpilot.databricks import DatabricksStore, DatabricksUnavailable


def change(event_id: str, commit: str = "c1") -> ChangeEvent:
    return ChangeEvent(event_id, ".", commit, None, "2026-09-06T00:00:00Z", ("service.py",), ("authenticate",), ("body_changed",), "SYNTHETIC", "phase5_fixture")


class HistoricalStoreTests(unittest.TestCase):
    def test_zero_data_is_unavailable_not_low_risk_evidence(self):
        evidence = InMemoryHistoricalStore().lookup(".", ("authenticate",), ("service.py",))
        self.assertFalse(evidence.available)
        self.assertEqual(evidence.sample_size, 0)
        self.assertIn("No relevant", evidence.limitations[0])

    def test_one_event_is_visible_but_adds_no_pattern_score(self):
        store = InMemoryHistoricalStore(); store.ingest((change("one"),), (), ())
        evidence = store.lookup(".", ("authenticate",), ("service.py",))
        risk = score_review((), (), evidence)
        self.assertTrue(evidence.available)
        self.assertEqual(risk.historical_component, 0)
        self.assertIn("Limited", evidence.limitations[0])

    def test_multiple_events_and_failure_add_deterministic_historical_score(self):
        store = InMemoryHistoricalStore()
        tests = (TestEvent("t1", ".", "c1", "2026-09-06T00:00:00Z", "python -m unittest auth", "authentication", "FAIL", 42, "assertion", "SYNTHETIC", "phase5_fixture"),)
        impacts = (ImpactSnapshot("i1", ".", "c1", "authenticate", "LoginHandler", "CALLS", 0.8, "package", "heuristic", "routes.py", 8, "2026-09-06T00:00:00Z", "SYNTHETIC", "phase5_fixture"),)
        store.ingest((change("one"), change("two", "c2"), change("three", "c3")), tests, impacts)
        evidence = store.lookup(".", ("authenticate",), ("service.py",))
        first, second = score_review((), (), evidence), score_review((), (), evidence)
        self.assertEqual(evidence.sample_size, 3)
        self.assertEqual(first.historical_component, second.historical_component)
        self.assertGreater(first.historical_component, 0)
        self.assertLessEqual(first.historical_component, 30)
        self.assertEqual(evidence.impact_patterns[0].trust_classification, "heuristic")

    def test_duplicate_ingestion_is_idempotent(self):
        store = InMemoryHistoricalStore(); event = change("same")
        store.ingest((event,), (), ()); store.ingest((event,), (), ())
        self.assertEqual(store.lookup(".", ("authenticate",), ("service.py",)).sample_size, 1)

    def test_unrelated_or_malformed_records_do_not_create_matches(self):
        store = InMemoryHistoricalStore(); store.ingest((ChangeEvent("bad", ".", "c", None, "now", (), (), (), "SYNTHETIC", "fixture"),), (), ())
        self.assertFalse(store.lookup(".", ("authenticate",), ("service.py",)).available)

    def test_databricks_without_configuration_fails_safely(self):
        with self.assertRaises(DatabricksUnavailable):
            DatabricksStore(host=None, token=None, warehouse_id=None).lookup(".", (), ())
