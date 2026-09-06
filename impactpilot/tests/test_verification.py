from __future__ import annotations

import unittest
from unittest.mock import patch

from impactpilot.graph.client import GraphClient, GraphClientError
from impactpilot.graph.verification import graph_verify_support


class VerificationTests(unittest.TestCase):
    def test_missing_graph_cli_is_an_explicit_error(self) -> None:
        with self.assertRaisesRegex(GraphClientError, "unavailable"):
            GraphClient(executable="definitely-not-entire-graph").run_json("neighbors", __import__("pathlib").Path("."))

    def test_windows_without_posix_shell_has_an_honest_fallback(self) -> None:
        with patch("impactpilot.graph.verification.os.name", "nt"), patch(
            "impactpilot.graph.verification.shutil.which", return_value=None
        ):
            support = graph_verify_support()
        self.assertFalse(support.available)
        self.assertIn("sh", support.reason)
        self.assertIn("test command", support.fallback)
