from __future__ import annotations

from pathlib import Path

from impactpilot.graph.client import GraphClient

from .intelligence import ProjectIntelligence, ProjectMap


class ProjectService:
    def __init__(self, client: GraphClient, *, max_nodes: int = 50) -> None:
        self.client, self.max_nodes = client, max_nodes

    def overview(self, repository: Path) -> ProjectMap:
        records = self.client.run_ndjson("snapshot", repository, "--format", "ndjson")
        return ProjectIntelligence().build(records, max_nodes=self.max_nodes)
