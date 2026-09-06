"""ImpactPilot's deliberately small Phase 4 command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from impactpilot.change.review import ReviewService
from impactpilot.graph.client import GraphClient


def main() -> int:
    parser = argparse.ArgumentParser(prog="impactpilot")
    command = parser.add_subparsers(dest="command", required=True)
    review = command.add_parser("review", help="Review one committed ref range using Entire Graph.")
    review.add_argument("--repo", type=Path, default=Path("."))
    review.add_argument("--base", required=True, help="Committed baseline ref; worktree comparisons are not implied.")
    review.add_argument("--head", required=True, help="Committed target ref.")
    review.add_argument("--graph-executable", default="entire-graph")
    review.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = ReviewService(GraphClient(args.graph_executable)).review(args.repo, base=args.base, head=args.head)
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
    print(f"Changed symbols: {len(result.changes)}; impact findings: {len(result.impact)}")
    for item in result.recommendations:
        print(f"{item.priority}. {item.action}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    raise SystemExit(main())
