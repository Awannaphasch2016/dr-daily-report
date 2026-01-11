# Research: Feature Integration Skill (Experiment-to-Codebase Mapping)

**Date**: 2026-01-10
**Focus**: workflow, knowledge management
**Status**: Complete

---

## Problem Decomposition

**Goal**: Create a skill/approach for mapping features from experiments or external repos to current codebase while:
1. Following current codebase standards
2. Preserving information during integration (no loss)
3. Providing systematic workflow (not ad-hoc)

**Why "migration" is wrong terminology**:
- "Migration" implies moving data/state from old to new (database migration, cloud migration)
- User's need is **adapting patterns/techniques** from source to target
- Focus is on **understanding + transformation**, not just copying

**Core Requirements**:
- [ ] Map concepts from source → target codebase
- [ ] Identify what to take vs what to leave
- [ ] Transform code to match local conventions
- [ ] Verify no information loss
- [ ] Document decisions made during process

**Constraints**:
- Source code may be different language (Python server-side → JavaScript client-side)
- Source architecture may violate local principles
- Source may lack documentation (must reverse-engineer intent)
- Local patterns must be respected (CLAUDE.md principles)

**Stakeholders**:
- Developer doing integration (wants clear workflow)
- Future maintainers (want to understand why decisions made)
- Codebase (wants consistency with existing patterns)

---

## Solution Space (Divergent Phase)

### Option 1: "Transplant" (Biological Metaphor)

**Description**: Like organ transplant - take working code from external source and graft it onto codebase with careful preparation to prevent rejection.

**How it works**:
1. **Tissue typing** - Assess compatibility (language, patterns, architecture)
2. **Preparation** - Prepare recipient site (identify integration points)
3. **Harvest** - Extract relevant components from donor
4. **Adaptation** - Modify to prevent rejection (adapt to local patterns)
5. **Verification** - Monitor for rejection (test, review)
6. **Documentation** - Record what was transplanted and why

**Pros**:
- Vivid metaphor that captures complexity
- Emphasizes careful preparation and compatibility checking
- Implies expertise required (not trivial)
- Captures idea of "foreign tissue" being integrated

**Cons**:
- Medical metaphor may feel dramatic for code
- "Rejection" implies failure (code doesn't have immune system)
- Less familiar term for developers

**Examples**:
- Transplanting stock-pattern library algorithms into JavaScript client-side code
- Transplanting authentication flow from external template

---

### Option 2: "Assimilate" (Integration Metaphor)

**Description**: Like cultural assimilation - absorb external patterns while transforming them to fit local culture (codebase conventions).

**How it works**:
1. **Understand source culture** - How does source code work? What are its idioms?
2. **Understand target culture** - What are local conventions? What principles apply?
3. **Identify transferable elements** - What techniques survive translation?
4. **Transform** - Rewrite in local idiom
5. **Validate** - Verify functionality preserved
6. **Integrate** - Merge into codebase

**Pros**:
- Emphasizes adaptation, not just copying
- Captures idea that source is transformed, not just moved
- Familiar term (Star Trek aside)

**Cons**:
- Can have negative connotations (forced cultural assimilation)
- May imply losing source identity entirely (we want to keep good parts)

---

### Option 3: "Adapt" (Pattern Adaptation)

**Description**: Focus on adapting patterns rather than code. Extract the technique, implement in local style.

**How it works**:
1. **Pattern extraction** - What problem does source solve? What's the technique?
2. **Context analysis** - How does it fit local architecture?
3. **Implementation design** - How would we solve this natively?
4. **Build** - Implement using local patterns
5. **Test** - Verify same functionality achieved
6. **Document** - Record source inspiration and local implementation

**Pros**:
- Clear focus on patterns/techniques over code
- Aligns with existing `/abstract` command philosophy
- Encourages understanding before coding
- Results in truly native code

**Cons**:
- May lose nuances from source implementation
- Requires more effort (re-implementation vs adaptation)
- Source code expertise required

**Real example from codebase**:
The `stock-pattern-library-learnings.md` file does exactly this:
- Analyzed stock-pattern library algorithms
- Extracted techniques (avgBarLength, Fibonacci validation, multiple validation layers)
- Documented how to implement in JavaScript
- DID NOT integrate library directly

---

### Option 4: "Port" (Software Porting)

**Description**: Traditional software porting - move code from one platform/language to another while preserving functionality.

**How it works**:
1. **Analyze source** - Understand functionality and dependencies
2. **Map APIs** - Identify equivalent APIs in target
3. **Translate code** - Convert syntax and idioms
4. **Adapt patterns** - Handle platform-specific differences
5. **Test equivalence** - Verify same behavior
6. **Optimize** - Improve for target platform

**Pros**:
- Well-understood term in software industry
- Clear goal (same functionality, different platform)
- Established practices exist

**Cons**:
- Implies 1:1 translation (may not want everything)
- Doesn't emphasize learning/documentation
- May encourage mechanical translation vs thoughtful adaptation

---

### Option 5: "Graft" (Horticultural Metaphor)

**Description**: Like grafting branches - attach external code onto existing codebase trunk, allowing it to grow with the system.

**How it works**:
1. **Select scion** (branch) - Choose what to integrate from source
2. **Prepare rootstock** (trunk) - Identify integration points in codebase
3. **Make cut** - Create clean interface for integration
4. **Join** - Connect scion to rootstock
5. **Heal** - Allow integration to stabilize
6. **Prune** - Remove unnecessary parts

**Pros**:
- Captures idea of external code becoming part of living system
- Emphasizes preparation of both source and target
- Implies ongoing relationship (not just copy-paste)

**Cons**:
- Less familiar metaphor for developers
- May over-emphasize permanence

---

### Option 6: "Ingest" (Data Processing Metaphor)

**Description**: Like data ingestion - take in external content, process it, transform it, store it in local format.

**How it works**:
1. **Extract** - Pull relevant content from source
2. **Transform** - Convert to local format/conventions
3. **Load** - Integrate into codebase
4. **Validate** - Verify correct transformation
5. **Document** - Record provenance and transformations

**Pros**:
- Familiar ETL pattern to developers
- Clear stages
- Emphasizes transformation

**Cons**:
- Implies passive data, not active patterns
- May feel mechanical

---

### Option 7: "Integrate" (with Mapping)

**Description**: Generic integration with explicit mapping documentation.

**How it works**:
1. **Source inventory** - List what source provides
2. **Target mapping** - Map to local equivalents/gaps
3. **Gap analysis** - Identify what's missing locally
4. **Integration plan** - Design how to bridge gaps
5. **Execute** - Implement integration
6. **Verify** - Test functionality
7. **Document** - Record mapping for future reference

**Pros**:
- Straightforward terminology
- Focuses on mapping (explicit knowledge preservation)
- Emphasizes planning before execution

**Cons**:
- "Integration" is very generic
- May not capture the experimental/learning aspect

---

## Evaluation Matrix

| Criterion | Transplant | Assimilate | Adapt | Port | Graft | Ingest | Integrate |
|-----------|------------|------------|-------|------|-------|--------|-----------|
| **Clarity of concept** | 7/10 | 6/10 | 9/10 | 8/10 | 6/10 | 7/10 | 7/10 |
| **Emphasizes learning** | 6/10 | 7/10 | 10/10 | 5/10 | 5/10 | 6/10 | 7/10 |
| **Information preservation** | 7/10 | 6/10 | 8/10 | 7/10 | 6/10 | 8/10 | 9/10 |
| **Fits existing workflow** | 7/10 | 6/10 | 9/10 | 7/10 | 6/10 | 6/10 | 8/10 |
| **Developer familiarity** | 5/10 | 6/10 | 8/10 | 9/10 | 4/10 | 7/10 | 9/10 |
| **Distinguishable name** | 8/10 | 7/10 | 6/10 | 7/10 | 8/10 | 8/10 | 4/10 |
| **Total** | **40** | **38** | **50** | **43** | **35** | **42** | **44** |

---

## Ranked Recommendations

### 1. "Adapt" - Pattern Adaptation Skill (Score: 50/60)

**Why this is best**:
- Aligns with existing philosophy: `/abstract` extracts patterns, `/adapt` applies them
- Emphasizes **understanding before implementing** (matches CLAUDE.md principles)
- Captures user's intent: "integrate techniques while following standards"
- Prevents "copy-paste without understanding" anti-pattern
- Results in truly native code (not foreign tissue)

**Trade-offs**:
- Gain: Clean native implementation, deep understanding, consistent codebase
- Lose: Speed (can't just copy), source nuances may be lost

**When to use**:
- Source is different language/architecture than target
- Learning the technique is more valuable than saving time
- Codebase has strong conventions that must be followed
- Source may have approaches that violate local principles

**Command name recommendation**: `/adapt` or `/assimilate`

**Workflow phases**:
1. **Study** - Understand source (what problem, what solution, why it works)
2. **Map** - Map source concepts to local equivalents
3. **Design** - Design local implementation using source techniques
4. **Implement** - Build in local style
5. **Verify** - Test same functionality achieved
6. **Document** - Record source, techniques adopted, decisions made

---

### 2. "Port" - Direct Translation (Score: 43/60)

**When to choose over Adapt**:
- Source and target are similar enough for direct translation
- Time-sensitive (need working code quickly)
- Source is well-tested and we want exact behavior
- Temporary integration (will refactor later)

**Trade-offs**:
- Gain: Speed, exact functionality preservation
- Lose: May not fit local conventions, may import problems

---

### 3. "Integrate with Mapping" - Explicit Mapping (Score: 44/60)

**When to choose**:
- Integration is primarily about connecting systems (not learning techniques)
- Need explicit documentation for compliance/audit
- Multiple sources being integrated simultaneously

**Trade-offs**:
- Gain: Explicit mapping document, traceable decisions
- Lose: May focus on mechanics over learning

---

## Proposed Skill Structure: `/adapt`

Based on analysis, here's the proposed skill:

### Command: `/adapt`

**Purpose**: Adapt techniques and patterns from external sources into the codebase while following local conventions and preserving knowledge.

**Arguments**:
```bash
/adapt "source" "goal"

# Examples:
/adapt "stock-pattern library" "chart pattern detection in frontend"
/adapt "https://github.com/user/repo" "authentication flow"
/adapt "experiment-branch" "PDF generation improvements"
```

**Phases**:

#### Phase 1: Study Source
- Clone/access source
- Analyze structure and purpose
- Identify key techniques and algorithms
- Document what problem source solves
- Rate quality and applicability

#### Phase 2: Map to Local Context
- Identify local equivalents for source concepts
- Find gaps (what source has that we don't)
- Find conflicts (where source violates our principles)
- Create concept mapping table

#### Phase 3: Design Local Implementation
- Design how to implement techniques locally
- Apply local patterns and conventions
- Identify what to take vs leave behind
- Create implementation plan

#### Phase 4: Implement
- Build using local patterns
- Add logging/observability per CLAUDE.md
- Add defensive programming per principles
- Write tests per testing-workflow skill

#### Phase 5: Verify
- Test functionality matches source intent
- Verify no regressions
- Check principle compliance
- Peer review

#### Phase 6: Document
- Record what was adapted
- Document techniques learned
- Link to source
- Explain decisions made

---

## Output Format

Create: `.claude/adaptations/{date}-{slug}.md`

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

## Integration with Existing Commands

### Complementary Workflow

```bash
# 1. Research sources (if multiple options)
/explore "chart pattern detection libraries"

# 2. Once chosen, adapt to codebase
/adapt "stock-pattern library" "chart pattern detection"

# 3. After adaptation, abstract learnings
/abstract ".claude/adaptations/*-chart-pattern*.md"

# 4. Evolve principles if significant
/evolve architecture
```

### Related Commands

| Command | Relationship |
|---------|-------------|
| `/explore` | Precedes `/adapt` - find sources to adapt |
| `/adapt` | **NEW** - adapt external sources to codebase |
| `/abstract` | Follows `/adapt` - extract patterns from adaptations |
| `/evolve` | Periodic review - incorporate learnings into principles |
| `/specify` | Alternative to `/adapt` when building from scratch |

---

## Real-World Validation

### Case Study: stock-pattern Library

The `.claude/research/2026-01-05-stock-pattern-library-learnings.md` file demonstrates this workflow:

**Phase 1 (Study)**: Analyzed library's detection algorithms
**Phase 2 (Map)**: Mapped Python patterns to JavaScript equivalents
**Phase 3 (Design)**: Designed local implementation with learnings:
- avgBarLength adaptive tolerance
- Fibonacci retracement validation
- Multiple validation layers
- Defensive data checks

**Phase 4 (Implement)**: Created `standalone_chart_viewer.html` improvements
**Phase 5 (Verify)**: Tested with real data
**Phase 6 (Document)**: Created comprehensive learnings document

**Key decision**: "DO NOT integrate library directly, DO adopt their techniques"

This validates the `/adapt` approach:
- Focus on techniques, not code transplant
- Respect local architecture (client-side JS, not server-side Python)
- Learn and apply, don't just copy

---

## Next Steps

```bash
# Create the skill
/specify "adapt command for external source integration"

# Or start using workflow manually with existing tools:
1. Create .claude/adaptations/ directory
2. Document source analysis in markdown
3. Create concept mapping table
4. Design local implementation
5. Implement and verify
6. Use /abstract to extract patterns after completion
```

---

## Decision

**Recommended approach**: Create `/adapt` command with 6-phase workflow

**Rationale**:
1. Fills gap in current command set (no systematic external integration)
2. Aligns with CLAUDE.md philosophy (understand before implement)
3. Prevents ad-hoc copy-paste integration
4. Creates documentation trail (`.claude/adaptations/`)
5. Validated by real-world case (stock-pattern library)

**Terminology decision**: Use "Adapt" over alternatives because:
- Clear action verb
- Emphasizes transformation, not copying
- Familiar to developers
- Fits with existing commands (`/abstract`, `/evolve`)

---

**Status**: Research complete. Ready for `/specify` to create detailed skill.
