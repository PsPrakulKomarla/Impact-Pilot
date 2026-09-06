"""Minimal Databricks SQL Statement Execution adapter, configured only by env vars."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from impactpilot.history.models import HistoricalEvidence
from impactpilot.history.store import HistoricalStore


class DatabricksUnavailable(RuntimeError): pass


class DatabricksStore(HistoricalStore):
    def __init__(self, host: str | None = None, token: str | None = None, warehouse_id: str | None = None) -> None:
        self.host = host or os.getenv("DATABRICKS_HOST")
        self.token = token or os.getenv("DATABRICKS_TOKEN")
        self.warehouse_id = warehouse_id or os.getenv("DATABRICKS_WAREHOUSE_ID")

    def _require_config(self) -> None:
        if not (self.host and self.token and self.warehouse_id):
            raise DatabricksUnavailable("Databricks configuration is unavailable; set DATABRICKS_HOST, DATABRICKS_TOKEN, and DATABRICKS_WAREHOUSE_ID.")

    def execute(self, statement: str) -> dict:
        self._require_config()
        request = urllib.request.Request(f"{self.host.rstrip('/')}/api/2.0/sql/statements", data=json.dumps({"statement": statement, "warehouse_id": self.warehouse_id, "wait_timeout": "30s"}).encode(), headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DatabricksUnavailable("Databricks SQL request failed; Graph-based review continues without history.") from exc

    def ingest(self, changes, tests, impacts) -> None:
        # A production caller supplies parameterized MERGE statements. Never silently substitute local storage.
        self._require_config()
        raise DatabricksUnavailable("Databricks ingestion requires a configured parameterized ingestion job.")

    def lookup(self, repository, symbols, files) -> HistoricalEvidence:
        self._require_config()
        raise DatabricksUnavailable("Databricks historical lookup is not available until the configured query job is deployed.")
