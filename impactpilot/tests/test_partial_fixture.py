from __future__ import annotations

import ast
import unittest
from pathlib import Path


class PartialAnalysisFixtureTests(unittest.TestCase):
    def test_fixture_uses_runtime_registration_not_a_fake_confidence_value(self) -> None:
        source = (Path(__file__).parent / "fixtures" / "partial_dynamic_dispatch.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertIn("getattr", calls)
        self.assertIn("import_module", calls)
        self.assertNotIn("confidence", source)
