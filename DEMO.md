# ImpactPilot demo — 3 to 5 minutes

## Safety before recording

- Use a clean terminal focused on this repository.
- Never show `.env`, Databricks credentials, or any previously exposed token. Rotate that token before submission.
- Label fixture data as a fixture and historical data as unavailable unless a real read-only query has been run.
- Use the local Graph binary if `entire graph` is not dispatched in the shell.

## 0:00–0:30 — Problem

“A diff tells me what lines changed. It does not tell me which callers, types, or related components I should inspect. ImpactPilot turns Entire Graph evidence into a focused review and verification plan.”

## 0:30–1:15 — Real semantic change

Show an actual semantic diff, for example:

```text
$graph diff --repo . --base HEAD~1 --head HEAD --json
```

Point out changed symbols, kinds, dependent counts, and warnings. Say that warnings constrain completeness rather than being hidden.

## 1:15–2:00 — Entire Graph impact evidence

Use the real small Go fixture for a compact, repeatable example:

```text
$graph def CheckToken --repo internal/sem/testdata/fixtures/go-basic --format json
$graph neighbors --repo internal/sem/testdata/fixtures/go-basic --symbol CheckToken --relation CALLS --direction both --format json
$graph impact --repo internal/sem/testdata/fixtures/go-basic --symbol CheckToken --format json
```

Show `LoginHandler → CheckToken`, its source location, confidence, resolution, and reason. State: “This is static structural evidence, not runtime proof.”

## 2:00–2:30 — Risk and recommendation

```text
python -m impactpilot review --repo . --base HEAD~1 --head HEAD --graph-executable $graph --json
```

Explain that risk factors are deterministic and capped: structural 60, history 30, verification 10. Do not claim historical evidence when it is unavailable.

## 2:30–3:00 — Project Intelligence

```text
python -m impactpilot project --repo . --graph-executable $graph --output project-map.html
```

Open the generated HTML. Show the bounded module map, click a module, then an edge. Explain that the panel preserves relationship type, confidence, resolution, reason, source evidence, and trust state.

## 3:00–3:40 — Curveball

Show `impactpilot/tests/fixtures/partial_dynamic_dispatch.py` and the relevant automated test. Say: “A runtime registry cannot be fully proved by static analysis. ImpactPilot labels incomplete/heuristic/unknown evidence and recommends source inspection plus targeted tests. Graph is evidence, not an oracle.”

## 3:40–4:20 — Historical Intelligence

Show `impactpilot/history/` and `impactpilot/databricks/`. State accurately: “The adapter is optional and preserves provenance. In this environment live Databricks history is not verified, so core Graph review continues with historical evidence unavailable.”

## 4:20–4:45 — Checkpoint context

```text
python -m impactpilot checkpoint --json
```

Show the actual checkpoint ID, recorded message, agent, date, and strategy. State the limitation: checkpoint context does not prove a test execution or safely map to a ref unless Entire provides it.

## 4:45–5:00 — Value

“Entire Graph tells us what is connected. ImpactPilot turns that evidence into what a developer should review, test, and verify—while making uncertainty visible.”

## Recording sequence

1. Semantic diff.
2. Definition, neighbors, and impact evidence.
3. ImpactPilot change review.
4. Generated Project Intelligence HTML.
5. Curveball fixture and uncertainty test.
6. Checkpoint context.
