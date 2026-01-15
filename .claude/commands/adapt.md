---
name: adapt
description: Adapt techniques and patterns from external sources into the codebase while following local conventions and preserving knowledge
accepts_args: true
arg_schema:
  - name: source
    required: true
    description: "External source to adapt from (URL, branch name, library name, or path)"
  - name: goal
    required: true
    description: "What you want to achieve in your codebase"
composition:
  - skill: research
---

# Adapt Command

**Extends**: [/transfer](transfer.md)
**Domain**: Code patterns, algorithms, techniques
**Transfer Type**: Heterogeneous (source type != target type)

---

## Purpose

Adapt techniques and patterns from external sources into the codebase while following local conventions and preserving knowledge.

**Core Philosophy**: Focus on techniques, not code transplant. Understand before implementing. The goal is to create truly native code that applies external techniques, not to copy foreign code.

---

## Relationship to /transfer Framework

This command is a **specialization** of the [/transfer](transfer.md) framework for code domains:

| Transfer Aspect | /adapt Value |
|-----------------|--------------|
| **Concept** | Technique, algorithm, pattern (variable) |
| **Source context** | External library, repo, docs, branch |
| **Target context** | Our codebase |
| **Transfer type** | Heterogeneous (source != target) |
| **Key challenge** | Preserve algorithm essence, change implementation |

The 7-step transfer process maps to our 6-phase workflow:
- Steps 1-2 (IDENTIFY, ANALYZE SOURCE) → Phase 1 (Study Source)
- Steps 3-4 (ANALYZE TARGET, MAP) → Phase 2 (Map to Local Context)
- Step 5 (UNTANGLE) → Phase 3 (Design Local Implementation)
- Step 6 (REWIRE) → Phase 4 (Implement)
- Step 7 (VERIFY) → Phases 5-6 (Verify, Document)

---

## When to Use

**Use /adapt when**:
- Integrating algorithms from a library (different language/architecture)
- Applying patterns from an experiment branch
- Learning from an external repo's approach
- Porting techniques from documentation or papers
- Adopting best practices from reference implementations

**Use /provision-env instead when**:
- Creating a new AWS environment (dev, staging, prod)
- Cloning infrastructure configuration
- See: [/provision-env](provision-env.md)

**Anti-pattern**: Blindly copying code without understanding → leads to unmaintainable "foreign tissue"

---

## Quick Reference

```bash
# From external repository
/adapt "https://github.com/user/repo" "authentication flow"

# From a library (not on PyPI)
/adapt "stock-pattern library" "chart pattern detection in frontend"

# From experiment branch
/adapt "experiment-branch" "PDF generation improvements"

# From documentation
/adapt "AWS SQS best practices" "message queue reliability"
```

---

## Six-Phase Workflow

### Phase 1: Study Source
**Transfer step**: IDENTIFY + ANALYZE SOURCE

**Goal**: Understand what the source provides and how it works

**Actions**:
1. Clone/access the source
2. Analyze structure, architecture, and dependencies
3. Identify key techniques and algorithms
4. Document what problem the source solves
5. Assess code quality, test coverage, and documentation

**Output**: Source analysis section in adaptation document

**Questions to answer**:
- What problem does this solve?
- What techniques does it use?
- Why does it work?
- What are its dependencies?
- How is it architected?

---

### Phase 2: Map to Local Context
**Transfer step**: ANALYZE TARGET + MAP

**Goal**: Create explicit mapping between source concepts and local equivalents

**Surface assumptions first with `/qna`**:
Before creating mappings, surface what you know and assume about both source and target:

```bash
/qna "adapting {source} for {goal}" moderate
```

This reveals:
- **Confident knowledge**: What you know about source and target
- **Assumptions**: Beliefs about compatibility that might be wrong
- **Knowledge gaps**: Missing information that could block adaptation

**Why `/qna` before mapping**: Hidden assumptions about source behavior or target constraints are the #1 cause of failed adaptations. Surfacing them early enables user correction.

**Actions**:
1. Run `/qna` to surface assumptions about source and target
2. Identify local equivalents for source concepts
3. Find gaps (what source has that we don't)
4. Find conflicts (where source violates our principles)
5. Create concept mapping table
6. Decide: adopt, skip, or adapt for each concept

**Output**: Concept mapping table

**Mapping decisions**:
| Action | When to use |
|--------|-------------|
| **Adopt** | Source technique aligns with local patterns |
| **Skip** | Source approach conflicts with local principles |
| **Adapt** | Source technique is valuable but needs modification |

---

### Phase 3: Design Local Implementation
**Transfer step**: UNTANGLE

**Goal**: Design how to implement techniques using local patterns

**Actions**:
1. Design architecture that fits existing codebase
2. Apply local patterns and conventions (from CLAUDE.md)
3. Identify files to create/modify
4. Document key design decisions with rationale
5. Create implementation plan

**Output**: Local implementation design

**Considerations**:
- Does it fit Aurora-First architecture? (Principle #3)
- Does it follow Error Handling Duality? (Principle #8)
- Will it need cross-boundary contract tests? (Principle #19)

---

### Phase 4: Implement
**Transfer step**: REWIRE

**Goal**: Build using local patterns and conventions

**Actions**:
1. Implement using local coding standards
2. Add logging per Storytelling Pattern (Principle #18)
3. Add defensive programming (Principle #1)
4. Write tests per testing-workflow skill (Principle #10)
5. Follow existing directory structure

**Output**: Working implementation

**Checklist**:
- [ ] Follows local naming conventions
- [ ] Uses local error handling patterns
- [ ] Has appropriate logging
- [ ] Includes defensive checks
- [ ] Has tests

---

### Phase 5: Verify
**Transfer step**: VERIFY

**Goal**: Confirm functionality matches source intent AND behavioral invariants hold

**Actions**:
1. Test functionality matches source behavior
2. Verify no regressions in existing code
3. Check principle compliance (CLAUDE.md)
4. Verify cross-boundary contracts (Principle #19)
5. Run full test suite
6. **Verify behavioral invariants** (Principle #25)

**Behavioral invariant verification with `/invariant`**:
Before claiming adaptation complete, verify invariants at all levels:

```bash
/invariant "adapted {goal} feature works correctly"
```

This generates a 5-level verification checklist:
- Level 4: Configuration (env vars, constants)
- Level 3: Infrastructure (Lambda → Aurora connectivity)
- Level 2: Data (schema, data conditions)
- Level 1: Service (API behavior, contracts)
- Level 0: User (end-to-end flow)

**Why `/invariant` before claiming "done"**: Adapted code may introduce implicit invariants that aren't obvious. `/invariant` makes them explicit so you verify them.

**Output**: Verification checklist

**Verification levels** (per Principle #2):
1. **Surface**: Tests pass (exit code 0)
2. **Content**: Output matches expected format
3. **Observability**: Logs show correct behavior
4. **Ground truth**: Actual behavior matches intent (verified via `/invariant`)

---

### Phase 6: Document
**Transfer step**: (Post-transfer documentation)

**Goal**: Record what was adapted for future reference

**Actions**:
1. Complete adaptation document
2. Record techniques learned (candidates for `/abstract`)
3. Link to source
4. Document decisions made and their rationale
5. Note lessons learned

**Output**: Complete adaptation document at `.claude/adaptations/`

---

## Execution Flow

### Step 1: Parse Arguments

```bash
/adapt "source" "goal"
```

- **source**: URL, library name, branch name, or description
- **goal**: What you want to achieve locally

### Step 2: Create Adaptation Document

Create: `.claude/adaptations/{date}-{slug}.md`

Initialize with:
- Date and status
- Source and goal
- Phase checklist

### Step 3: Execute Phases Sequentially

Work through each phase:
1. Study → complete source analysis
2. Map → complete concept mapping
3. Design → complete local design
4. Implement → complete code changes
5. Verify → complete verification checklist
6. Document → complete documentation

**Checkpoints**: Update document after each phase. If blocked, document the blocker and ask for guidance.

### Step 4: Generate Summary

After completion:
```
✅ Adaptation complete

Source: {source}
Goal: {goal}

Techniques adopted:
- {technique 1}
- {technique 2}

Files created/modified:
- {file 1}
- {file 2}

Output: .claude/adaptations/{file}

Next steps:
- Run /abstract to extract patterns for reuse
- Consider updating CLAUDE.md if significant learning
```

---

## Adaptation Document Template

```markdown
# Adaptation: {Goal}

**Date**: {date}
**Source**: {URL or description}
**Status**: {planning | in_progress | complete | abandoned}

---

## Source Analysis

**What source provides**:
- {Feature 1}
- {Feature 2}
- {Technique 1}

**What problem it solves**:
{Description}

**Source architecture**:
{How source works}

**Quality assessment**:
- Code quality: {score}/10
- Test coverage: {score}/10
- Documentation: {score}/10
- Principle alignment: {score}/10

---

## Concept Mapping

### Knowledge State (from /qna)

**Confident** (verified facts):
- {Fact about source}
- {Fact about target}

**Assumed** (inferred, verify with user):
- {Assumption about source behavior}
- {Assumption about target constraints}

**Unknown** (knowledge gaps):
- {Gap that could block adaptation}

### Mapping Table

| Source Concept | Local Equivalent | Gap/Conflict | Action |
|----------------|------------------|--------------|--------|
| {concept} | {equivalent} | {none/gap/conflict} | {adopt/skip/adapt} |
| ... | ... | ... | ... |

**Key techniques to adopt**:
1. {Technique} - {Why valuable}
2. {Technique} - {Why valuable}

**Things to skip**:
1. {Thing} - {Why skipping}
2. {Thing} - {Why skipping}

**Conflicts to resolve**:
1. {Conflict} - {How resolving}

---

## Local Implementation Design

**Where it fits in architecture**:
{Description}

**Files to create/modify**:
- `path/to/file.py` - {What}
- `path/to/file.py` - {What}

**Design decisions**:
1. {Decision} - {Rationale}
2. {Decision} - {Rationale}

---

## Implementation Progress

- [ ] Phase 1: Study source
- [ ] Phase 2: Create mapping
- [ ] Phase 3: Design implementation
- [ ] Phase 4: Implement
- [ ] Phase 5: Verify
- [ ] Phase 6: Document

---

## Verification

**Tests added**:
- `test_file.py::test_function`

**Principle compliance**:
- [ ] Defensive programming (Principle #1)
- [ ] Evidence strengthening (Principle #2)
- [ ] Logging discipline (Principle #18)
- [ ] Behavioral invariants verified (Principle #25)

**Behavioral invariants** (from /invariant):
| Level | Invariant | Status |
|-------|-----------|--------|
| 4 (Config) | {env var set} | [ ] Verified |
| 3 (Infra) | {connectivity works} | [ ] Verified |
| 2 (Data) | {schema valid} | [ ] Verified |
| 1 (Service) | {API contract} | [ ] Verified |
| 0 (User) | {end-to-end flow} | [ ] Verified |

**Functionality verified**:
- [ ] {Feature 1 works}
- [ ] {Feature 2 works}

---

## Lessons Learned

**What worked well**:
- {Insight 1}

**What was challenging**:
- {Challenge 1}

**Techniques for future**:
- {Technique} - {Application}

---

## References

- Source: {URL}
- Related: {internal docs}
- Discussion: {PR/issue if any}
```

---

## Examples

### Example 1: Adapting Library Algorithms

```bash
/adapt "stock-pattern library" "chart pattern detection in frontend"
```

**Scenario**: Python library with pattern detection algorithms, need JavaScript implementation for client-side charts.

**Phase 1 (Study)**:
- Library provides 9 pattern detection algorithms
- Uses pivot points for pattern recognition
- Validates with Fibonacci retracements
- Quality: High code, good tests, minimal docs

**Phase 2 (Map)**:
| Source | Local | Gap/Conflict | Action |
|--------|-------|--------------|--------|
| Python detection class | JS service | Language gap | Adapt |
| Server-side processing | Client-side | Architecture gap | Adapt |
| Pandas DataFrames | Array data | Type gap | Adapt |
| Raw pattern output | Structured API | Interface gap | Adapt |

**Key decision**: "DO NOT integrate library directly, DO adopt their techniques"

**Phase 3 (Design)**:
- Create `pattern_detection_service.py` wrapper
- Add to `ReportResponse.chart_patterns`
- Keep library server-side, send results to frontend

**Outcome**: Native implementation using library techniques

---

### Example 2: Adapting from Experiment Branch

```bash
/adapt "feature/pdf-v2" "improved PDF generation"
```

**Scenario**: Experiment branch has working PDF generation with performance improvements.

**Phase 1 (Study)**:
- New template system with chunked rendering
- 3x faster than current implementation
- Uses different caching strategy

**Phase 2 (Map)**:
| Source | Local | Gap/Conflict | Action |
|--------|-------|--------------|--------|
| Chunk rendering | None | Gap | Adopt |
| Template caching | Redis cache | Conflict (we use Aurora) | Adapt |
| New dependencies | None | Gap | Evaluate |

**Phase 3 (Design)**:
- Adopt chunk rendering (technique)
- Skip Redis caching (conflicts with Aurora-First)
- Adapt caching to use Aurora tables instead

---

### Example 3: Adapting from External Repository

```bash
/adapt "https://github.com/example/auth-template" "OAuth2 flow"
```

**Scenario**: Reference implementation of OAuth2 that needs to fit local patterns.

**Phase 1 (Study)**:
- Complete OAuth2 implementation
- Uses Express.js (we use FastAPI)
- Has good test coverage
- Includes refresh token handling

**Phase 2 (Map)**:
| Source | Local | Gap/Conflict | Action |
|--------|-------|--------------|--------|
| Express routes | FastAPI routes | Framework gap | Adapt |
| JWT tokens | Same | None | Adopt |
| Session storage | Aurora tables | Architecture gap | Adapt |
| Error responses | Local format | Interface gap | Adapt |

**Decision**: Reimplement in FastAPI using same OAuth2 flow logic

---

## Error Handling

### Source Not Accessible

```bash
/adapt "https://github.com/private/repo" "feature"
```

**Response**:
```
❌ Cannot access source: https://github.com/private/repo

Options:
1. Ensure you have access to the repository
2. Clone locally and provide local path
3. Provide alternative source URL
4. Describe the techniques you want to adapt
```

### Source Too Complex

**Response**:
```
⚠️ Source is complex (50+ files, multiple modules)

Recommendations:
1. Focus on specific component: /adapt "repo/src/auth" "auth flow"
2. Break into multiple adaptations
3. Start with core technique, expand later

Which approach would you prefer?
```

### Conflict with Local Principles

**Response**:
```
⚠️ Source approach conflicts with CLAUDE.md principles:

Conflict: Source uses silent fallbacks (violates Principle #1)
Source: Returns default on error
Local: Should raise exception

Recommendations:
1. Adapt: Use source algorithm, add fail-fast error handling
2. Skip: Don't adopt this technique
3. Override: Document exception to principle (requires justification)

Which approach for this conflict?
```

---

## Integration with Other Commands

### Workflow: Explore → Adapt → Abstract

```bash
# 1. Find sources to adapt from
/explore "chart pattern detection libraries"

# 2. Once chosen, adapt to codebase
/adapt "stock-pattern library" "chart pattern detection"

# 3. After adaptation, extract reusable patterns
/abstract ".claude/adaptations/*-chart-pattern*.md"

# 4. If significant learning, evolve principles
/evolve architecture
```

### Related Commands

| Command | Relationship |
|---------|-------------|
| `/explore` | Precedes `/adapt` - find sources to adapt |
| `/adapt` | **THIS** - adapt external sources to codebase |
| `/abstract` | Follows `/adapt` - extract patterns from adaptations |
| `/evolve` | Periodic review - incorporate learnings into principles |
| `/specify` | Alternative when building from scratch |

---

## Directory Structure

```
.claude/
├── adaptations/           # Adaptation documents
│   ├── README.md          # Adaptation process overview
│   ├── 2026-01-05-stock-pattern-integration.md
│   └── 2026-01-10-oauth2-flow.md
```

---

## Principles

### 1. Understand Before Implementing
Never copy code without understanding why it works. Phase 1 (Study) is mandatory.

### 2. Map Explicitly
Always create concept mapping table. This prevents hidden assumptions and documents decisions.

### 3. Respect Local Conventions
Source code is inspiration, not law. Local patterns take precedence.

### 4. Document Decisions
Record why you adopted, skipped, or adapted each concept. Future maintainers need this.

### 5. Verify Thoroughly
Don't assume adaptation worked. Test against source intent using Progressive Evidence (Principle #2).

### 6. Extract Learnings
After adaptation, run `/abstract` to capture reusable patterns. One adaptation can benefit many future projects.

---

## Real-World Validation

**Case Study**: stock-pattern Library Integration (2026-01-05)

This command design was validated by the stock-pattern library integration:

1. **Phase 1 (Study)**: Analyzed library's 9 detection algorithms
2. **Phase 2 (Map)**: Mapped Python patterns to JavaScript equivalents
3. **Phase 3 (Design)**: Designed wrapper service maintaining local patterns
4. **Phase 4 (Implement)**: Created `pattern_detection_service.py`
5. **Phase 5 (Verify)**: Tested with real data
6. **Phase 6 (Document)**: Created comprehensive learnings document

**Key insight from case study**: "DO NOT integrate library directly, DO adopt their techniques"

See:
- `.claude/research/2026-01-05-stock-pattern-library-learnings.md`
- `.claude/research/2026-01-09-pattern-integration-complete.md`

---

## See Also

### Transfer Framework
- [/transfer](transfer.md) - Abstract transfer framework (parent)
- [/provision-env](provision-env.md) - Infrastructure transfer (sibling specialization)

### Key Integrations
- [/qna](qna.md) - Surface assumptions in Phase 2 (Map to Local Context)
- [/invariant](invariant.md) - Verify behavioral invariants in Phase 5 (Verify)

### Related Commands
- `.claude/commands/abstract.md` - Extract patterns from adaptations
- `.claude/commands/evolve.md` - Incorporate learnings into principles
- `.claude/commands/explore.md` - Find sources to adapt
- `.claude/commands/specify.md` - Design from scratch (alternative)

### Supporting Resources
- `.claude/skills/research/` - Research methodology
- `.claude/adaptations/README.md` - Adaptation document index
- [Contextual Transfer Framework](../abstractions/workflow-2026-01-11-contextual-transfer-framework.md) - Abstract theory
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md) - Invariant verification methodology
