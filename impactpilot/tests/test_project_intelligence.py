from __future__ import annotations

import unittest

from impactpilot.graph.client import GraphClient, GraphClientError
from impactpilot.project import ProjectIntelligence, render_html


def records(partial: bool = False):
    return (
        {"schema_version": "1.1", "repo_root": "sample", "commit": "abc", "warnings": [], "partial_failures": []},
        {"record_type": "file", "id": "file:a", "path": "auth/service.py"},
        {"record_type": "file", "id": "file:b", "path": "routes/login.py"},
        {"record_type": "symbol", "id": "s:a", "name": "AuthService", "kind": "class", "file_path": "auth/service.py", "start_line": 7},
        {"record_type": "symbol", "id": "s:b", "name": "LoginRoute", "kind": "function", "file_path": "routes/login.py", "start_line": 3},
        {"record_type": "relation", "from_id": "s:b", "to_id": "s:a", "type": "CALLS", "confidence": .8, "resolution": "package", "reason": "direct call", "evidence": [{"file_path": "routes/login.py", "start_line": 3}]},
        {"record_type": "relation", "from_id": "s:a", "to_id": "s:b", "type": "HANDLES_ROUTE", "confidence": .8, "resolution": "exact", "reason": "route", "evidence": []},
        {"record_type": "summary", "warnings": [], "partial_failures": ([{"code": "parse"}] if partial else []), "stats": {"files": 2, "symbols": 2, "relations": 2, "completeness_level": "partial" if partial else "ok"}},
    )


class ProjectIntelligenceTests(unittest.TestCase):
    def test_aggregates_real_snapshot_shape_and_preserves_trust(self):
        project = ProjectIntelligence().build(records())
        self.assertEqual(2, len(project.nodes))
        self.assertEqual(2, len(project.edges))
        confirmed = next(edge for edge in project.edges if "CALLS" in edge.types)
        heuristic = next(edge for edge in project.edges if "HANDLES_ROUTE" in edge.types)
        self.assertEqual(1, confirmed.trust["confirmed"])
        self.assertEqual(1, heuristic.trust["heuristic"])
        self.assertEqual("AuthService", project.search("auth")[0]["name"])
        context = project.context("module:auth")
        self.assertIn("auth/service.py", context["relevant_files"])

    def test_partial_coverage_becomes_visible_in_edge_trust_and_warning(self):
        project = ProjectIntelligence().build(records(partial=True))
        self.assertEqual("partial", project.coverage)
        self.assertTrue(project.warnings)
        self.assertIn("incomplete", project.edges[0].trust)

    def test_visible_node_bound_and_html_has_interactions(self):
        expanded = list(records()[:-1])
        for index in range(5): expanded.append({"record_type": "file", "id": f"x:{index}", "path": f"extra{index}/a.py"})
        expanded.append(records()[-1])
        project = ProjectIntelligence().build(tuple(expanded), max_nodes=2)
        self.assertEqual(2, len(project.nodes))
        html = render_html(project)
        self.assertIn("Relationship evidence", html)
        self.assertIn("AI Context", html)


class GraphClientNdjsonTests(unittest.TestCase):
    def test_malformed_ndjson_is_rejected(self):
        client = GraphClient("missing-command")
        with self.assertRaises(GraphClientError):
            client.run_ndjson("snapshot", __import__("pathlib").Path("."))
