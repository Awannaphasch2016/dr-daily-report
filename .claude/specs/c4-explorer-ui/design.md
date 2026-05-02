---
title: C4 Diagram Explorer UI — Design Spec
status: deferred / pending user input on confirmation Q1–Q4
date: 2026-04-28
author: anak (designed with Claude during /tf-aws audit follow-up session)
related:
  - .claude/journals/architecture/2026-04-28-tf-aws-blind-spots-documented.md
  - docs/architecture/c4-plantuml/rendered/orphan_audit_2026-04-28.html
  - .claude/replicas/dr-bot.yaml
tags: [ui, c4, diagram-explorer, replica-audit, deferred]
---

# C4 Diagram Explorer UI — Design Spec

## Status

**Deferred.** User has paused implementation to work on other tasks. This file is the durable spec so the design can be picked up cold without requiring conversation history. **Before implementing, answer Q1–Q4 in §10.**

## 1. Problem framing (rephrase of intent)

Build a **single durable system-knowledge UI** where the **C4 hierarchy is the spine** and **rich annotations hang off specific nodes and edges** of each diagram. Replace the workflow of "produce a fresh stand-alone HTML for every audit run" (e.g. `orphan_audit_2026-04-28.html`) with **one explorer where data updates while structure stays put**.

Concretely:

1. **Four tabs** — Context, Container, Component, Class — clicking a tab swaps the main diagram to that C4 level. Same system, four zoom levels.
2. **Each tab combines two halves**: diagram (top/main) + annotation sections (below/side) that talk about specific nodes/edges in that diagram. Annotations are the things diagrams structurally cannot carry — finding tables, narrative investigation, coverage gaps, out-of-scope items, recommended next steps.
3. **`orphan_audit_2026-04-28.html` is one cell** of a bigger matrix — specifically the (Component-level × audit-perspective) cell for the dr-bot replica. The UI generalizes this into the full matrix.
4. **Bidirectional link is load-bearing**: diagram is the coordinate system, annotations are coordinates in that system. Click a node → annotations highlight. Click an annotation → its node highlights.
5. **Long-term**: layer multiple perspectives (audit, performance, compliance, runtime health, …) over the same diagram set. Audit is just the first perspective.

## 2. Page layout (visual)

```
┌──────────────────────────────────────────────────────────────────────┐
│  dr-bot ▼   Perspective: Audit ▼   Run: 2026-04-28 ▼   Search: [_] │  ← top bar
├──────────────────────────────────────────────────────────────────────┤
│ [Context] [Container] [Component]* [Class]                           │  ← C4 tabs
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│              ┌──────────────────────────────────┐                    │
│              │                                  │                    │
│              │      Mermaid C4 diagram          │                    │
│              │   (clickable nodes + edges)      │  ← diagram pane    │
│              │                                  │     (sticky)       │
│              │                                  │                    │
│              └──────────────────────────────────┘                    │
├──────────────────────────────────────────────────────────────────────┤
│  [Imported] [Drifted] [Post-audit findings] [Coverage gap]           │  ← anchor
│  [Out of scope] [Recommended next steps]                             │     chips
├──────────────────────────────────────────────────────────────────────┤
│  ## Imported tables                                                  │
│  (annotations anchored to specific diagram nodes; clicking a row     │
│   highlights the linked node above)                                  │
│                                                                      │
│  ## Drifted (D1)  ← anchored to node `lambda_telegram_api`           │
│  ...                                                                 │
│                                                                      │
│  ## Recommended next steps                                           │
└──────────────────────────────────────────────────────────────────────┘
```

Diagram pane is sticky on scroll so annotations and diagram stay co-visible.

## 3. The full matrix

The current single audit HTML occupies one cell of a 4-axis matrix:

```
      ┌─────────────── Replica ─────────────────┐
      │  dr-bot │ webapp │ frontend │  …        │
      ├─────────┴────────┴──────────┴───────────┤
      │  Perspective                             │
      │  ├─ audit          (TF↔AWS reconcile)    │
      │  ├─ performance    (latency hotspots)    │
      │  ├─ compliance     (policy gates)        │
      │  ├─ runtime-health (live errors)         │
      │  └─ …                                    │
      ├──────────────────────────────────────────┤
      │  C4 level                                │
      │  ├─ Context        (system-of-systems)   │
      │  ├─ Container      (deployable units)    │
      │  ├─ Component      (modules per unit)    │
      │  └─ Class          (code-level structure)│
      ├──────────────────────────────────────────┤
      │  Node anchor                             │
      │  ├─ component / container ID             │
      │  └─ edge ID (between components)         │
      └──────────────────────────────────────────┘

orphan_audit_2026-04-28.html ≈ (dr-bot, audit, Component, *)
                                   one cell, all nodes for that cell
```

Today: one HTML per audit. Goal: one explorer; (replica, perspective, run) is data; (C4 level, node anchor) is structure.

## 4. Bidirectional linking (visual)

```
                        ┌──────────────────────────┐
                        │  Diagram (coordinate sys) │
                        │                           │
                        │     [node:lambda_api] ◄───┼──┐
                        │            │              │  │ click annotation
                        │            ▼              │  │ → highlight node
                        │     [edge:lambda→aurora]  │  │
                        │                           │  │
                        └──────────────────────────┘  │
                                  ▲                    │
                                  │ click node         │
                                  │ → scroll/expand    │
                                  │   linked annot     │
                                  │                    │
                        ┌─────────┴──────────────────┴┐
                        │  Annotations (coordinates)   │
                        │                              │
                        │  - D1 Drifted env vars       │
                        │    @ lambda_api              │
                        │                              │
                        │  - O7 Orphan API GW          │
                        │    @ apigw_telegram          │
                        │                              │
                        │  - Edge note: latency 2.3s   │
                        │    @ lambda→aurora           │
                        └──────────────────────────────┘
```

The anchor field on each annotation is a **node ID or edge ID** in the diagram. Stable IDs are the coupling. The ID schema lives in §6.

## 5. Data model

```yaml
# annotations/<replica>/<perspective>/<run-id>.yaml

replica: dr-bot
perspective: audit
run_id: "2026-04-28"
generated_at: "2026-04-28T10:11:00Z"

annotations:
  - id: D1
    section: drifted
    title: "telegram-api Lambda env vars: OPENROUTER_API_KEY, PDF_STORAGE_BUCKET"
    c4_level: component
    anchor:
      type: node
      id: lambda_telegram_api
    body_md: |
      Phase C2 fingerprint diff shows env var disagreement.
      OPENROUTER_API_KEY: declared in TF, no consumer in code (trim-spec candidate)
      PDF_STORAGE_BUCKET: declared in TF, real consumer at src/api/transformer.py
                          but missing from AWS env (refresh-tf or apply-tf)
    verdict: review                       # apply-tf | refresh-tf | review | informational | trim-spec
    severity: medium
    plug: "Plug #2 — journal before destructive verb"

  - id: O7
    section: orphan
    title: "Orphan API GW: dr-daily-report-telegram-api-dev"
    c4_level: container
    anchor:
      type: node
      id: apigw_telegram
    body_md: |
      Listed in AWS, absent from TF replica scope.
      Three checks needed before import: stg/prd parity,
      CI override, stray invokers.
    verdict: review
    severity: low
```

```yaml
# diagrams/<replica>/<c4-level>.mmd
# Mermaid C4 source with node/edge IDs that match annotation anchors

C4Component
  Container_Boundary(c, "Telegram API") {
    Component(lambda_telegram_api, "Lambda")          %% ← anchor
    Component(apigw_telegram, "API GW HTTP")          %% ← anchor
  }
  Rel(apigw_telegram, lambda_telegram_api, "invokes") %% ← edge anchor: apigw_telegram→lambda_telegram_api
```

**Stable ID rule**: node IDs must be stable across runs. Annotations point at IDs; if IDs churn, links break.

## 6. Migration map (from current artifact to new structure)

```
orphan_audit_2026-04-28.html               .claude/specs/c4-explorer-ui/...
─────────────────────────────────          ──────────────────────────────────────
Header chips (ORPHAN, DRIFTED…)     ───►   Section anchor chips in tab footer
Imported tables block                ───►   annotation.section: imported
DRIFTED panel (D1)                   ───►   annotation.section: drifted, anchor=node
Post-audit findings                  ───►   annotation.section: post_audit
Coverage gap                         ───►   annotation.section: coverage_gap
Out of scope (runtime symptoms)      ───►   annotation.section: out_of_scope
Recommended next steps               ───►   annotation.section: recommendations
                                            (verdict: apply-tf | refresh-tf | trim-spec | review)
PlantUML rendered SVG                ───►   diagrams/dr-bot/component.mmd (Mermaid)
```

The migration is **lossless** for content but **changes the substrate** from a static HTML to a (diagram, annotations) pair.

## 7. Tech stack recommendation

### Phase 1 MVP — single self-contained HTML + JSON (recommended)

- **One static HTML file** with vanilla JS — no build step, no SPA framework
- **Mermaid 10.x** loaded from CDN for diagram rendering
- **Hash-based routing** (`#/dr-bot/audit/2026-04-28/component`) so URLs are shareable and deep-linkable
- **Annotations + diagrams** as adjacent JSON/YAML files; HTML fetches them at load
- **No backend** — runs from `file://` or any static host (S3, GitHub Pages)
- **Why**: matches the "one durable explorer" goal without taking on a frontend build pipeline. Audit data is read-mostly; SPA overhead isn't justified yet.

### Phase 2 (defer until needed)

- Trigger only when ≥2 of these hold:
  - Multi-user collab on annotations (real-time)
  - Annotation editing in-browser (write path, not just read)
  - Cross-replica search beyond a few thousand annotations
  - Auth required (audit findings are sensitive)
- Stack at that point: small SPA (Svelte or solid-js) + a lightweight read-only API. Don't pre-build this.

## 8. File layout (proposed)

```
.claude/specs/c4-explorer-ui/
├── design.md                        ← this file
├── data-model.md                    ← (optional) split out of §5 when richer
└── prototypes/
    └── 2026-04-28-mvp/              ← Phase 1 MVP lives here
        ├── index.html               ← shell + tabs + Mermaid host
        ├── app.js                   ← router, fetcher, link logic
        ├── diagrams/
        │   └── dr-bot/
        │       ├── context.mmd
        │       ├── container.mmd
        │       ├── component.mmd
        │       └── class.mmd
        └── annotations/
            └── dr-bot/
                └── audit/
                    └── 2026-04-28.yaml
```

## 9. Open design questions (Q1–Q7)

These can be deferred to implementation time but are listed so the implementer doesn't rediscover them:

- **Q1** — How are diagrams authored? Hand-written Mermaid vs auto-generated from Terraform/code? (Auto-gen long-term; hand-written for MVP.)
- **Q2** — How are stable node IDs generated when diagrams regenerate? (Hash of `(c4_level, container, name)` is the working answer.)
- **Q3** — Where do annotations come from for the audit perspective? Hand-written today; generated by `/tf-aws audit` long-term?
- **Q4** — Run ID semantics: is each `/tf-aws audit` invocation a new "run", or do we overwrite latest? (Suggest: keep history, default-show latest.)
- **Q5** — Can annotations span perspectives? (e.g. an annotation that's both audit-relevant and performance-relevant.) Default no — duplicate if needed.
- **Q6** — Edge anchors vs node anchors: when an annotation talks about a relationship (e.g. "lambda → aurora latency"), what's the anchor syntax? (Suggest: `node:A→B` for the directed edge.)
- **Q7** — Search/filter: free-text across annotation bodies, or structured filters (severity, verdict, section)? Both eventually; structured first.

## 10. Confirmation questions before implementing (Q1–Q4 must be answered)

These resolve "did I understand the intent." Implement only after these are answered.

- **C1** — **Is the matrix in §3 the right framing?** Specifically: is "perspective" (audit / performance / compliance / runtime-health) a first-class axis, or is the user only thinking about the audit perspective for now? (Design treats it as first-class but Phase 1 only ships audit.)
- **C2** — **Is the bidirectional linking in §4 load-bearing for MVP, or nice-to-have?** Implementing click-node-highlights-annotation is straightforward; click-annotation-highlights-node requires id-driven scroll + Mermaid SVG manipulation. Confirm this is must-have for v1.
- **C3** — **Phase 1 stack: single-file HTML + JSON?** Or does the user want a SPA build pipeline (Vite/Svelte/etc.) from day one? (Recommend single-file HTML; explicit confirm preferred.)
- **C4** — **Where does this live?** Three candidates:
  - (a) Inside the repo at `.claude/specs/c4-explorer-ui/prototypes/...` (versioned with code, simple)
  - (b) `docs/architecture/c4-explorer/` (lives next to existing C4 PlantUML output)
  - (c) Standalone repo `dr-daily-report-c4-explorer` (separable concern, separable lifecycle)
  - Recommend (b) once promoted out of MVP; (a) for MVP.

## 11. Out of scope (explicit non-goals for v1)

- Editing annotations in-browser (read-only; edit via files + git)
- Real-time collaboration / presence
- Auth (assume audit findings can be shared with team)
- Cross-replica join queries (one replica at a time)
- Diff between two runs (e.g. "what changed between 2026-04-28 and 2026-05-15") — Phase 2
- Auto-generation of diagrams from Terraform — Phase 2 (Q1)
- Auto-generation of audit annotations from `/tf-aws audit` — Phase 2 (Q3)

## 12. Composition with existing knowledge artifacts

| Existing artifact | Role in explorer |
|---|---|
| `.claude/replicas/dr-bot.yaml` | Source of truth for replica scope, fingerprint fields |
| `.claude/commands/tf-aws.md` "Blind spots and limits" | Composes with explorer: each blind spot becomes a perspective layer (or annotation tag) once data exists |
| `orphan_audit_2026-04-28.html` | Migration source; first audit run imported into the new model |
| `.claude/journals/architecture/2026-04-28-tf-aws-blind-spots-documented.md` | Plug #2 entry — explorer is the durable surface that prevents re-deriving findings |
| Principle #25 (Behavioral Invariant) | Annotations can carry an `invariant_level` field (0–4) for envelope visibility |
| Principle #28 (Compositional Hierarchy) | Tier-0 = diagram; Tier-1 = annotation; Tier-2 = perspective; Tier-3 = matrix; explorer makes the tiering explicit |

## 13. When you resume

1. Read this file top to bottom.
2. Answer C1–C4 in §10.
3. Skim Q1–Q7 in §9 — defer most, decide Q1, Q3 if they affect MVP.
4. Build `prototypes/<date>-mvp/` per §8.
5. Migrate `orphan_audit_2026-04-28.html` content to `annotations/dr-bot/audit/2026-04-28.yaml` per §6.
6. Hand-author `diagrams/dr-bot/component.mmd` with stable node IDs matching the annotation anchors.
7. Verify Layer 4: open `index.html`, click a node, confirm linked annotation highlights; click an annotation, confirm node highlights.

---

**End of spec.** Implementation paused; spec is self-contained.
