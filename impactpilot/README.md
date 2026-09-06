# ImpactPilot Evidence Trust Layer

ImpactPilot consumes Entire Graph JSON through a Python subprocess adapter and
normalizes it before later intelligence phases can use it. It does not change
Entire Graph's semantic engine.

## Data flow

```text
Entire Graph CLI → GraphClient → normalize_graph_output → evaluate_evidence → verification fallback
```

## Classification rules

These are **ImpactPilot policy**, not reinterpretations of provider confidence:

- `incomplete`: the result explicitly has partial failures, reports a
  `degraded`, `partial`, or `failed` completeness level, or says a bounded
  neighbors result was truncated.
- `heuristic`: the relationship type appears in Entire Graph's reported
  `heuristic_relation_types` capability (`HANDLES_ROUTE`, `HTTP_CALLS`,
  `EMITS`, `LISTENS_ON`, `HANDLES_TOOL`, `SIMILAR_TO`, or `TESTS`).
- `unknown`: the result does not explicitly establish complete analysis, or is
  missing a relationship type, target, confidence, or resolution.
- `confirmed`: only a complete result with non-heuristic relationship metadata.
  This means *confirmed structural evidence*, never confirmed runtime truth.

Numeric confidence is preserved but never thresholded by ImpactPilot.

Warnings are preserved for auditability. They become `unknown` unless an
explicit partial failure or completeness signal says the analysis is partial;
the provider does not document every warning as a coverage failure.

## Graph consumption map

| Future component | Entire Graph command | Evidence retained |
| --- | --- | --- |
| Change Intelligence | `diff --json` | entity change records, dependent counts, warnings and partial results |
| Impact Intelligence | `impact --format json` | callers, callees, type/data-flow findings and result coverage |
| Relationship context | `neighbors --format json` | relation, confidence, resolution, reason, call-site/evidence |
| Source lookup | `def --format json`, `search --format json` | symbol/source location for verification |
| Verification | `verify` | availability and the provider verdict; never a fabricated success |

Phase 3 fully flattens the current `neighbors` JSON shape. It retains any
other command result unchanged as UNKNOWN evidence until the owning later
phase supplies its command-specific interpretation; this prevents an impact
or semantic-diff result from being accidentally promoted to a certainty.

## Fixtures and verification

`tests/fixtures/partial_dynamic_dispatch.py` demonstrates a real static
analysis limitation: the selected handler comes from runtime registry data.
No missing relationship is interpreted as proof that no runtime call exists.
The contract fixture models the provider's explicit partial coverage signals.

On Windows without `sh`, graph verification is unavailable. The fallback is to
run the targeted test directly and inspect the cited source; that state is
returned explicitly, never as success.
