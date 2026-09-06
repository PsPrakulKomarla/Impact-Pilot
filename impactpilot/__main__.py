"""ImpactPilot's deliberately small Phase 4 command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from impactpilot.change.review import ReviewService
from impactpilot.checkpoint import CheckpointError, EntireCheckpointClient
from impactpilot.graph.client import GraphClient
from impactpilot.project import render_html
from impactpilot.project.service import ProjectService


def main() -> int:
    parser = argparse.ArgumentParser(prog="impactpilot")
    command = parser.add_subparsers(dest="command", required=True)
    review = command.add_parser("review", help="Review one committed ref range using Entire Graph.")
    review.add_argument("--repo", type=Path, default=Path("."))
    review.add_argument("--base", required=True, help="Committed baseline ref; worktree comparisons are not implied.")
    review.add_argument("--head", required=True, help="Committed target ref.")
    review.add_argument("--graph-executable", default="entire-graph")
    review.add_argument("--databricks", action="store_true", help="Use configured Databricks SQL historical intelligence.")
    review.add_argument("--json", action="store_true")
    project = command.add_parser("project", help="Create a bounded, evidence-preserving project map from an Entire Graph snapshot.")
    project.add_argument("--repo", type=Path, default=Path("."))
    project.add_argument("--graph-executable", default="entire-graph")
    project.add_argument("--max-nodes", type=int, default=50)
    project.add_argument("--output", type=Path, help="Write a self-contained interactive HTML map.")
    project.add_argument("--json", action="store_true")
    checkpoint = command.add_parser("checkpoint", help="Show read-only context from an actual Entire checkpoint.")
    checkpoint.add_argument("--id", help="Checkpoint ID; defaults to the latest checkpoint on this branch.")
    checkpoint.add_argument("--entire-executable", default="entire")
    checkpoint.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.command == "project":
        try:
            result = ProjectService(GraphClient(args.graph_executable), max_nodes=args.max_nodes).overview(args.repo)
        except Exception as exc:
            print(f"Project Intelligence unavailable: {exc}")
            return 2
        if args.output:
            args.output.write_text(render_html(result), encoding="utf-8")
            print(f"Wrote interactive project map: {args.output}")
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=str))
        elif not args.output:
            print(f"PROJECT INTELLIGENCE: {result.total_files} files, {result.total_symbols} symbols, {result.total_relations} relationships")
            print(f"Coverage: {result.coverage}; visible modules: {len(result.nodes)}")
            for node in result.nodes:
                print(f"- {node.label}: {len(node.files)} files, {node.incoming + node.outgoing} inter-module relationships")
        return 0
    if args.command == "checkpoint":
        try:
            client = EntireCheckpointClient(args.entire_executable)
            result = client.get(args.id) if args.id else client.latest()
        except CheckpointError as exc:
            print(f"Checkpoint context unavailable: {exc}")
            return 2
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print("IMPACTPILOT CHECKPOINT CONTEXT")
            print(f"ID: {result.checkpoint_id}; state: {result.message or 'not recorded'}")
            print(f"Agent: {result.agent or 'not recorded'}; strategy: {result.strategy or 'not recorded'}")
            print(f"Sessions: {result.session_count if result.session_count is not None else 'not recorded'}; recorded checkpoints: {result.checkpoint_count if result.checkpoint_count is not None else 'not recorded'}")
            for limitation in result.limitations: print(f"Limitation: {limitation}")
        return 0
    historical_store = None
    if args.databricks:
        from impactpilot.databricks import DatabricksStore
        historical_store = DatabricksStore()
    result = ReviewService(GraphClient(args.graph_executable), historical_store=historical_store).review(args.repo, base=args.base, head=args.head)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        _render(result)
    return 0 if result.status in {"complete", "no_semantic_changes"} else 2


def _render(result) -> None:
    print("IMPACTPILOT CHANGE REVIEW")
    print(f"Baseline: {result.baseline} -> {result.target} ({result.status})")
    if result.risk:
        print(f"Risk: {result.risk.level} - {result.risk.score}/100")
        print(f"Historical: {result.risk.historical_status} ({result.risk.historical_component}/30)")
    print(f"Changed symbols: {len(result.changes)}; impact findings: {len(result.impact)}")
    for item in result.recommendations:
        print(f"{item.priority}. {item.action}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    raise SystemExit(main())
