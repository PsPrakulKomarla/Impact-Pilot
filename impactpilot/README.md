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

## Phase 4 change review

Run a review over two **committed refs** (not an implied worktree comparison):

```text
python -m impactpilot review --repo . --base <commit-or-ref> --head <commit-or-ref> --graph-executable entire-graph
```

The workflow calls `diff --json`, then bounded `impact` and `neighbors`
queries for up to 20 non-deleted changed symbols. `impact` determines direct
and transitive shape; `neighbors` provides the relationship confidence,
resolution, reason, and source evidence required by the Trust Layer. Deleted
symbols are not queried as though they still exist; the review requests manual
inspection of their prior callers.

The result is available as human-readable output or `--json`. It includes the
explicit baseline and target refs, changed symbols, impact findings and raw
evidence, trust classification, deterministic risk factors, recommendations,
and a verification plan.

### Deterministic decision-support score

Risk is bounded to 0–100: structural evidence can contribute up to 60 points,
and verification uncertainty up to 10. The Phase 2 historical allocation is
intentionally **0 / unavailable** until Phase 5 provides real historical data.
The score is not predictive: every contribution is exposed with its signal,
value, reason, and Entire Graph source.

- Signature/body/removal/rename semantic changes contribute documented fixed
  amounts (18/8/15/12), because they represent distinct change types from the
  provider—not confidence thresholds.
- Provider-reported dependent counts, direct impact, and transitive impact add
  capped structural contributions.
- Every non-confirmed impact finding adds a verification component and source/
  graph re-check actions. Unknown or incomplete evidence is never equivalent
  to “no impact.”

Risk levels are LOW 0–29, MEDIUM 30–59, HIGH 60–79, and CRITICAL 80–100.

## Phase 5 historical intelligence / Databricks

Databricks is an optional historical enhancement, never a dependency of the
Graph review. Its narrow Delta tables are `change_events`, `test_events`, and
`impact_snapshots`; each record includes repository/commit provenance, capture
time, source, and an explicit `REAL`, `SYNTHETIC`, or `REPRESENTATIVE` label.

Configure the production adapter only through environment variables (never
commit them): `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, and
`DATABRICKS_WAREHOUSE_ID`. Then opt in:

```text
python -m impactpilot review --repo . --base <ref> --head <ref> --databricks
```

If configuration, authentication, or SQL is unavailable, the core review
continues and reports historical intelligence as unavailable. The local
`InMemoryHistoricalStore` exists solely for deterministic tests and fixtures;
it never claims to be Databricks or real historical data.

Historical scoring is a documented **ImpactPilot policy**: 0 for no data or a
single event; for two or more related change events, recurrence contributes up
to 10 points, recurring impact snapshots up to 8, and associated historical
test failures up to 12 (total capped at 30). Every factor includes its sample
size. A historical heuristic snapshot stays heuristic—it never confirms a
current relationship or predicts a failure.

## Phase 6 project intelligence

`impactpilot project` consumes the actual `entire-graph snapshot --format ndjson`
stream. It does not parse source code or maintain another dependency graph. The
initial map groups files by their first repository directory, bounds visible
modules (50 by default), aggregates only inter-module relations, and retains a
representative relation's type, confidence, resolution, reason, and source
evidence. Click a module or relationship in the generated HTML to inspect that
evidence, trust classification, symbol locations, and a compact Graph-derived
AI context selection.

```text
python -m impactpilot project --repo . --graph-executable entire-graph --output project-map.html
```

The renderer is plain self-contained HTML/SVG/JavaScript: the repository had no
web app or frontend dependencies, so this is the smallest portable interactive
surface for the hackathon. It supports bounded initial rendering, click-to-drill
down, relationship evidence, symbol/file search, reset, and a focused context
view. It deliberately does not claim runtime completeness, token savings, or
full-repository rendering scalability. Partial Graph results are surfaced as a
coverage warning and classify relationship evidence as `incomplete`; heuristic
provider relation families remain visibly heuristic.
