# C4-PlantUML Diagrams — Daily DR Ticker Report

Source `.puml` files for the AWS-deployed daily ticker report system. Uses the
[C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) standard library
(included via `!include` URL — no local install needed).

## Files

| File | C4 Level | Scope |
|------|----------|-------|
| `c4_context.puml` | L1 Context | Users, the system as a black box, external services |
| `c4_container.puml` | L2 Container | All AWS containers (Lambdas, Step Functions, Aurora, S3, DynamoDB, API Gateway, CloudFront) |
| `c4_component_report_worker.puml` | L3 Component | Internals of the Report Worker Lambda |
| `c4_dynamic_daily_pipeline.puml` | Dynamic | Numbered flow of the 08:00 BKK daily pipeline |

## Rendering

```bash
./scripts/render-c4-diagrams.sh
```

Downloads `tools/plantuml.jar` on first run (gitignored), then renders every
`.puml` to SVG under `rendered/`. Uses the bundled Smetana layout engine, so
no Graphviz install needed. Requires Java 11+.

## Source of truth

These diagrams are hand-curated from `terraform/`, `src/`, and the architecture
exploration in CLAUDE.md. They complement the existing Structurizr DSL
(`docs/architecture/workspace.dsl`) and IcePanel generator
(`scripts/generate_c4_diagrams.py`) — pick whichever tool fits your workflow.
