from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from impactpilot.checkpoint import CheckpointError, EntireCheckpointClient


class CheckpointTests(unittest.TestCase):
    def test_latest_combines_actual_entire_list_and_explain_contracts(self):
        responses = [
            json.dumps([{"checkpoint_id": "real-123", "message": "stable review", "agent": "Codex", "date": "2026-09-06"}]),
            json.dumps({"checkpoint_id": "real-123", "strategy": "manual-commit", "session_count": 1, "checkpoints_count": 2}),
        ]
        with patch("impactpilot.checkpoint.subprocess.run", side_effect=[subprocess.CompletedProcess([], 0, text, "") for text in responses]):
            result = EntireCheckpointClient().latest()
        self.assertEqual("real-123", result.checkpoint_id)
        self.assertEqual("stable review", result.message)
        self.assertEqual("manual-commit", result.strategy)
        self.assertTrue(result.limitations)

    def test_missing_entire_is_human_readable(self):
        with patch("impactpilot.checkpoint.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(CheckpointError, "executable not found"):
                EntireCheckpointClient().latest()
