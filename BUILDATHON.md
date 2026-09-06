# ImpactPilot — Track 2: Build with Graph Intelligence

## Summary

ImpactPilot turns Entire Graph's static repository evidence into an evidence-first developer workflow: semantic changes, bounded impact, trust classification, explainable risk, recommended verification, project mapping, optional historical context, and checkpoint context.

## Problem and users

A normal diff shows lines that changed but not the structural relationships that may be affected. ImpactPilot is for developers reviewing a change in an unfamiliar or large codebase who need a bounded answer to: what changed, what is connected, what should be reviewed, and what still requires verification.

## Why Entire Graph is essential

Entire Graph supplies the semantic symbols, relationships, confidence/resolution, source evidence, semantic diff, and bounded impact that ImpactPilot consumes. Without it, ImpactPilot would be reduced to Git diff plus manual review; it would not have Graph-derived callers, callees, type consumers, or relationship provenance.

```text
Entire Graph → GraphClient → evidence normalization → trust gate
             → change review → risk → recommendations / verification
             → project map / AI context
             → checkpoint context (development state)
```

## Product capabilities

- Change Intelligence: committed-ref semantic diff, bounded `impact` and `neighbors` queries, explainable risk and recommendations.
- Trust Layer: `confirmed`, `heuristic`, `incomplete`, and `unknown` are distinct. Numeric confidence is preserved and never treated as runtime certainty.
- Curveball: dynamic dispatch and partial-analysis fixtures result in a verification recommendation rather than a certainty claim.
- Historical Intelligence: optional Databricks-oriented models, schemas, and a safe unavailable fallback. Historical records carry `REAL`, `SYNTHETIC`, or `REPRESENTATIVE` provenance.
- Project Intelligence: actual Entire Graph NDJSON snapshot → bounded directory/module map → inspectable relationship evidence and focused context. The static HTML/SVG view starts with aggregated modules, not every symbol.
- Checkpoints: read-only context from `entire checkpoint list/explain --json`; no checkpoint/ref or test-execution mapping is invented.

## Real Graph evidence observed (VERIFIED)

On 2026-09-06, the local Entire Graph binary returned a definition for `CheckToken` at `auth.go:16`, and its neighbors returned `LoginHandler → CheckToken` (`CALLS`, confidence `0.8`, resolution `package`, evidence `server.go:11-17`) plus `CheckToken → Token.Validate` (`CALLS`, confidence `0.85`, resolution `type_inferred`). Its impact response reported one direct caller and one callee.

The current repository semantic diff also reported real added checkpoint classes/methods, a changed `main` function, dependent counts, and an explicit warning that `.gitignore` policy changes can affect graph completeness.

## Run

The installed `entire` CLI is enabled but currently does not dispatch `entire graph`; use the registered local provider binary in this environment:

```text
$graph = 'C:\Users\prakul\AppData\Local\entire\plugins\bin\entire-graph.exe'
python -m unittest discover -s impactpilot/tests -v
python -m impactpilot review --repo . --base HEAD~1 --head HEAD --graph-executable $graph --json
python -m impactpilot project --repo . --graph-executable $graph --output project-map.html
python -m impactpilot checkpoint --json
```

## Verification and data disclosure

- Unit/regression suite: **37 passed** on 2026-09-06 (VERIFIED).
- Current project-map extraction: **669 files, 12,843 symbols, 60,430 relationships**, initially aggregated to **15 modules**; provider coverage reported `partial` (VERIFIED).
- Databricks: code and schema exist, but no live query/data was validated in this run (NOT VERIFIED). It must remain read-only unless explicit validation requires more; rotate any token that was previously exposed.
- Token/context reduction: NOT VERIFIED. The product reports bounded files/context, not token savings.
- Windows Graph verification can be unavailable when POSIX `sh` is absent; the fallback reports this honestly (VERIFIED by tests).

## Known limitations

Static Graph evidence does not prove runtime behavior. Dynamic dispatch, reflection, generated code, and partial coverage require source inspection and targeted tests. Checkpoint data describes recorded work but does not itself prove a specific test ran. The current visual UI is a dependency-free static HTML/SVG artifact rather than a hosted web service.

## Future improvements

Deploy the configured Databricks query job, provide a supported Entire CLI/plugin-dispatch combination, add a narrow hosted UI only if needed, and record reproducible performance benchmarks across target repositories.
