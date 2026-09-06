"""Aggregate actual Entire Graph snapshot records into bounded project views."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from impactpilot.graph.evidence import EvidenceQuality, analysis_status, normalize_graph_output
from impactpilot.graph.trust import evaluate_evidence


@dataclass(frozen=True)
class ProjectNode:
    id: str
    label: str
    kind: str
    files: tuple[str, ...]
    symbols: tuple[dict[str, Any], ...]
    incoming: int
    outgoing: int
    trust: dict[str, int]


@dataclass(frozen=True)
class ProjectEdge:
    id: str
    source: str
    target: str
    types: tuple[str, ...]
    count: int
    trust: dict[str, int]
    evidence: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ProjectMap:
    repository: str | None
    state: str
    coverage: str
    warnings: tuple[str, ...]
    nodes: tuple[ProjectNode, ...]
    edges: tuple[ProjectEdge, ...]
    symbols: tuple[dict[str, Any], ...]
    total_files: int
    total_symbols: int
    total_relations: int

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "nodes": [asdict(n) for n in self.nodes], "edges": [asdict(e) for e in self.edges]}

    def search(self, query: str) -> tuple[dict[str, Any], ...]:
        needle = query.lower().strip()
        if not needle:
            return ()
        results = [s for s in self.symbols if needle in str(s.get("name", "")).lower() or needle in str(s.get("file_path", "")).lower()]
        return tuple(results[:50])

    def context(self, target: str) -> dict[str, Any]:
        node = next((n for n in self.nodes if n.id == target or n.label == target), None)
        if not node:
            raise KeyError(target)
        linked = {node.id}
        for edge in self.edges:
            if edge.source == node.id: linked.add(edge.target)
            if edge.target == node.id: linked.add(edge.source)
        selected = [n for n in self.nodes if n.id in linked]
        files = tuple(sorted({f for item in selected for f in item.files}))
        return {
            "repository": self.repository, "target": {"id": node.id, "label": node.label},
            "relevant_files": files[:20], "excluded_file_count": max(0, self.total_files - len(files)),
            "relationships": [asdict(e) for e in self.edges if e.source in linked and e.target in linked],
            "recommended_inspection_order": [
                {"file": f, "reason": "It belongs to the selected or directly connected Graph-derived module."} for f in files[:12]
            ],
            "coverage": self.coverage,
        }


class ProjectIntelligence:
    """A projection layer only: it consumes snapshot records, never parses source."""

    def build(self, records: tuple[Mapping[str, Any], ...], *, max_nodes: int = 50) -> ProjectMap:
        if max_nodes < 1:
            raise ValueError("max_nodes must be positive")
        header = next((r for r in records if "schema_version" in r), {})
        summary = next((r for r in records if r.get("record_type") == "summary"), {})
        context = dict(header) | dict(summary)
        files = [dict(r) for r in records if r.get("record_type") == "file"]
        symbols = [dict(r) for r in records if r.get("record_type") == "symbol"]
        relations = [dict(r) for r in records if r.get("record_type") == "relation"]
        paths = {r["id"]: r.get("path", "") for r in files if isinstance(r.get("id"), str)}
        symbol_by_id = {r["id"]: r for r in symbols if isinstance(r.get("id"), str)}
        for item in symbols:
            paths[item.get("id", "")] = item.get("file_path", "")
        groups: dict[str, list[str]] = defaultdict(list)
        for item in files:
            path = str(item.get("path", ""))
            groups[_module(path)].append(path)
        symbol_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in symbols:
            symbol_groups[_module(str(item.get("file_path", "")))].append(_symbol_view(item))
        aggregate: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        trust_by_module: dict[str, Counter[str]] = defaultdict(Counter)
        for relation in relations:
            origin = _module(str(paths.get(relation.get("from_id"), "")))
            destination = _module(str(paths.get(relation.get("to_id"), "")))
            if not origin or not destination or origin == destination:
                continue
            evidence = normalize_graph_output({**context, "record_type": "relation", **relation}, command="snapshot") [0]
            trust = evaluate_evidence(evidence).quality.value
            aggregate[(origin, destination)].append({"type": relation.get("type"), "trust": trust, "confidence": relation.get("confidence"), "resolution": relation.get("resolution"), "reason": relation.get("reason"), "evidence": relation.get("evidence", [])})
            trust_by_module[origin][trust] += 1; trust_by_module[destination][trust] += 1
        degree = Counter()
        for (source, target), items in aggregate.items(): degree[source] += len(items); degree[target] += len(items)
        chosen = sorted(groups, key=lambda key: (-degree[key], key))[:max_nodes]
        chosen_set = set(chosen)
        incoming, outgoing = Counter(), Counter()
        edges: list[ProjectEdge] = []
        for (source, target), items in aggregate.items():
            if source not in chosen_set or target not in chosen_set: continue
            outgoing[source] += len(items); incoming[target] += len(items)
            types = tuple(sorted({str(x.get("type")) for x in items if x.get("type")}))
            trusts = Counter(str(x["trust"]) for x in items)
            edges.append(ProjectEdge(f"{source}->{target}", f"module:{source}", f"module:{target}", types, len(items), dict(trusts), tuple(items[:10])))
        nodes = tuple(ProjectNode(f"module:{key}", key, "module", tuple(sorted(groups[key])), tuple(symbol_groups[key][:100]), incoming[key], outgoing[key], dict(trust_by_module[key])) for key in chosen)
        stats = summary.get("stats", {}) if isinstance(summary.get("stats"), Mapping) else {}
        status = analysis_status(context).value
        warnings = tuple(str(x) for x in context.get("warnings", ()) if x) + tuple("Partial Graph analysis detected; verify critical paths against source and targeted tests." for _ in context.get("partial_failures", ()) )
        return ProjectMap(header.get("repo_root"), header.get("commit") or header.get("tree") or "working tree", status, warnings, nodes, tuple(edges), tuple(_symbol_view(s) for s in symbols), int(stats.get("files", len(files))), int(stats.get("symbols", len(symbols))), int(stats.get("relations", len(relations))))


def _module(path: str) -> str:
    parts = PurePosixPath(path.replace("\\", "/")).parts
    return parts[0] if len(parts) > 1 else "repository root"


def _symbol_view(item: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item.get(key) for key in ("id", "name", "qualified_name", "kind", "file_path", "start_line", "end_line", "signature")}
