# What-If Analysis: Reorganize .claude/skills/ by Type

**Date**: 2025-12-25
**Type**: Architecture (folder structure)
**Assumption**: Separate generalized and domain-specific skills into subdirectories

---

## Current Reality

### Current Structure
```
.claude/skills/
├── code-review/              # Generalized
├── database-migration/       # Domain-specific
├── deployment/               # Domain-specific
├── error-investigation/      # Hybrid
├── line-uiux/                # Domain-specific
├── refactor/                 # Generalized
├── research/                 # Generalized
├── telegram-uiux/            # Domain-specific
└── testing-workflow/         # Generalized
```

**Properties**:
- **Flat structure**: All skills at same level (`.claude/skills/{name}/`)
- **9 skills total**: 4 generalized, 4 domain-specific, 1 hybrid
- **Auto-discovery**: Claude scans `.claude/skills/*/SKILL.md`
- **References**: 22 files reference skill paths (`.claude/skills/{name}`)

**Sources**:
- File listing: `find .claude/skills -type f -name "SKILL.md"`
- References: `grep -r "\.claude/skills/"` (22 files)
- Discovery pattern: Documented in explorations/skills-vs-mcp-modularity-principles.md

---

## Under New Assumption: Organize by Type

### Proposed Structure (Option 1: Nested by Type)
```
.claude/skills/
├── generalized/
│   ├── code-review/
│   ├── refactor/
│   ├── research/
│   └── testing-workflow/
└── domain-specific/
    ├── database-migration/
    ├── deployment/
    ├── error-investigation/    # Hybrid - classify as domain-specific
    ├── line-uiux/
    └── telegram-uiux/
```

**Path changes**:
- Before: `.claude/skills/research/SKILL.md`
- After: `.claude/skills/generalized/research/SKILL.md`

---

## What Changes Immediately

### File System
- All skill directories move to subdirectories
- Depth increases: 2 levels → 3 levels
- Path structure: `.claude/skills/{type}/{name}/SKILL.md`

### References
- 22 files contain hardcoded skill paths
- All references need updating:
  - `.claude/CLAUDE.md` (references to skill paths)
  - `.claude/commands/*.md` (references to skills)
  - `.claude/explorations/*.md` (documentation)
  - `docs/*.md` (technical documentation)

### Discovery Mechanism
- **Critical unknown**: How does Claude Code discover skills?
  - Pattern A: `.claude/skills/*/SKILL.md` (one level only) ❌ Would break
  - Pattern B: `.claude/skills/**/SKILL.md` (recursive) ✅ Would work
  - Pattern C: Hardcoded list ❌ Would require Claude Code update

---

## What Breaks

### Critical Failures (IF discovery is non-recursive)

#### **Skill auto-discovery failure**
- **Impact**: Claude cannot find skills (none auto-discovered)
- **Frequency**: 100% of skill invocations
- **Severity**: Critical (entire skill system broken)
- **Workaround**: None (requires Claude Code update)
- **Evidence**: If discovery pattern is `.claude/skills/*/SKILL.md` (one-level glob)

**Cascading effects**:
```
Skills not discovered
  → Claude doesn't apply methodologies
    → /bug-hunt doesn't work
    → /refactor doesn't work
    → Error investigation patterns unavailable
      → Debugging degraded to manual trial-and-error
```

---

### Reference Breakage (Certain)

#### **Hardcoded skill paths in documentation**
- **Files affected**: 22 files
- **Impact**: Broken links, incorrect documentation
- **Severity**: Medium (documentation issue, not runtime)
- **Workaround**: Update all references (1-2 hours work)

**Examples**:
```markdown
Before: See [code-review skill](.claude/skills/code-review/DEFENSIVE.md)
After:  See [code-review skill](.claude/skills/generalized/code-review/DEFENSIVE.md)
```

**Files requiring updates**:
- `.claude/CLAUDE.md` (~10 references)
- `.claude/commands/README.md` (~5 references)
- `.claude/explorations/*.md` (~7 files with references)
- `docs/*.md` (~3 files with references)

---

### Workflow Disruption (Certain)

#### **Mental model change for navigation**
- **Before**: "Go to `.claude/skills/{name}`"
- **After**: "Go to `.claude/skills/{type}/{name}` (need to know type first)"
- **Impact**: Cognitive overhead (must classify skill first)
- **Frequency**: Every time browsing/editing skills
- **Severity**: Low-Medium (annoying, not blocking)

**Example**:
```bash
# Before (direct)
cd .claude/skills/deployment

# After (requires type knowledge)
cd .claude/skills/domain-specific/deployment  # Is it generalized or domain-specific?
```

---

## What Improves

### Conceptual Clarity

#### **Type distinction made visible**
- **Benefit**: Folder structure reflects architectural distinction
- **Value**: Newcomers see two types of skills immediately
- **Magnitude**: Educational (helps understanding)

**Example**:
```
.claude/skills/
├── generalized/     # "Oh, these are methodologies!"
└── domain-specific/ # "Oh, these are domain expertise!"
```

---

### Scalability Potential

#### **Clearer organization as skills grow**
- **Current**: 9 skills (manageable in flat structure)
- **At 20 skills**: Flat structure getting cluttered
- **At 50 skills**: Nested structure more maintainable

**Scenario analysis**:
| # Skills | Flat Structure | Nested by Type |
|----------|----------------|----------------|
| 9 (now) | ✅ Easy | ⚠️ Over-engineered |
| 20 | ⚠️ Cluttered | ✅ Clear grouping |
| 50 | ❌ Overwhelming | ✅ Organized |

**Current state**: 9 skills (still in "easy" range for flat structure)

---

### Type-Specific Documentation

#### **Could add type-specific README files**
- `skills/generalized/README.md` - "How to create methodology skills"
- `skills/domain-specific/README.md` - "How to create domain skills"

**Value**: Educational for skill creators

---

## Insights Revealed

### Assumptions Exposed

#### **Hidden Assumption 1: Discovery mechanism is unknown**
- **Evidence**: No documentation on how Claude Code discovers skills
- **Risk**: Reorganization could break discovery entirely
- **Criticality**: High (showstopper if discovery is non-recursive)
- **Need**: Validate discovery pattern BEFORE reorganizing

**Test needed**:
```bash
# Create test skill in nested directory
mkdir -p .claude/skills/test-category/test-skill
echo "---\nname: test-skill\n---\nTest skill" > .claude/skills/test-category/test-skill/SKILL.md

# Check if Claude discovers it
# If YES → recursive discovery ✅
# If NO → one-level discovery only ❌
```

---

#### **Hidden Assumption 2: Flat structure is "good enough" for now**
- **Evidence**: Only 9 skills currently (manageable without nesting)
- **Implicit**: We assumed skills would proliferate rapidly
- **Reality**: Skill creation is infrequent (9 skills over months)
- **Consequence**: Premature optimization if we reorganize now

---

#### **Hidden Assumption 3: Type classification is stable**
- **Evidence**: error-investigation is hybrid (both generalized + domain)
- **Problem**: Where does it go? Forced choice creates ambiguity
- **Insight**: Binary classification (generalized vs domain) oversimplifies

**Example edge cases**:
- `error-investigation`: Generalized methodology + AWS domain
- Future: `api-design`: Could be generalized (REST principles) or domain-specific (FastAPI patterns)

Classification forces a choice that may not be clean.

---

### Trade-offs Clarified

#### **Clarity vs Simplicity**
- **Nested structure**: More conceptual clarity (types visible)
- **Flat structure**: More operational simplicity (shorter paths)
- **Current choice**: Flat (simplicity over clarity)
- **Validation**: ✅ Correct for 9 skills (not yet cluttered)

---

#### **Future-proofing vs YAGNI**
- **Nested structure**: Prepares for 50+ skills
- **Flat structure**: Sufficient for current 9 skills
- **Question**: Will we ever have 50+ skills?
- **Answer**: Unknown (could be 15 skills in 1 year, or 20 in 5 years)
- **YAGNI principle**: "You Aren't Gonna Need It" (don't optimize prematurely)

---

### Boundary Conditions

#### **Flat structure manageable up to ~15 skills**
- **Threshold**: Beyond 15 skills, flat structure gets cluttered
- **Current**: 9 skills (60% of threshold)
- **Growth rate**: ~2-3 skills per quarter (based on recent history)
- **Time to threshold**: ~2 quarters (~6 months)

**Projection**:
```
Now: 9 skills (manageable)
+3 months: 11 skills (still manageable)
+6 months: 13 skills (approaching threshold)
+9 months: 15 skills (at threshold, consider reorganizing)
+12 months: 17 skills (flat structure suboptimal)
```

---

### Design Rationale

#### **Why flat structure exists**:
1. **Simplicity**: Direct paths (`.claude/skills/{name}`)
2. **Discoverability**: All skills at same level (easy to browse)
3. **Historical**: Created before type distinction was identified
4. **Sufficient**: 9 skills don't require organization

#### **Why nested might be needed later**:
1. **Scale**: At 20+ skills, grouping helps
2. **Conceptual model**: Types are real architectural distinction
3. **Documentation**: Type-specific READMEs would help creators

**Conclusion**: Flat was right choice initially, nested may be right choice later.

---

## Alternative Structures Considered

### Option 2: Prefix Naming (Flat with Prefixes)
```
.claude/skills/
├── g-code-review/         # g = generalized
├── g-refactor/
├── g-research/
├── g-testing-workflow/
├── d-database-migration/  # d = domain-specific
├── d-deployment/
├── d-line-uiux/
└── d-telegram-uiux/
```

**Pros**:
- ✅ Type visible in name
- ✅ No path changes (same depth)
- ✅ No discovery risk
- ✅ Alphabetically grouped by type

**Cons**:
- ❌ Ugly naming convention (`g-`, `d-` prefixes)
- ❌ Doesn't match command naming (no prefixes there)
- ❌ Type in two places (prefix + folder name)

---

### Option 3: Metadata-Only (No Structural Change)
```
.claude/skills/
├── code-review/
│   └── SKILL.md  # Add: type: generalized
├── refactor/
│   └── SKILL.md  # Add: type: generalized
...
```

**Add to SKILL.md frontmatter**:
```yaml
---
name: research
type: generalized
scope: "Systematic investigation methodology for any problem"
---
```

**Pros**:
- ✅ Type documented without path changes
- ✅ Queryable (can list skills by type)
- ✅ No discovery risk
- ✅ No reference updates needed

**Cons**:
- ❌ Type not visible in file browser
- ❌ Doesn't help with 50-skill clutter problem

---

### Option 4: Hybrid (Metadata + Nesting Later)
```
Phase 1 (Now): Add metadata to SKILL.md
Phase 2 (At 15+ skills): Migrate to nested structure
```

**Pros**:
- ✅ Type documented now (metadata)
- ✅ Can reorganize later if needed
- ✅ No premature optimization
- ✅ Graceful migration path

**Cons**:
- ❌ Eventual migration still has reference-update cost
- ❌ Two-phase approach (more work total)

---

## Discovery Mechanism Investigation

### Critical Unknown: How Does Claude Code Discover Skills?

**Hypotheses**:

#### Hypothesis A: One-level glob (`.claude/skills/*/SKILL.md`)
- **If true**: Nested structure BREAKS discovery ❌
- **Evidence needed**: Test nested skill, check if discovered

#### Hypothesis B: Recursive glob (`.claude/skills/**/SKILL.md`)
- **If true**: Nested structure WORKS ✅
- **Evidence needed**: Same test, different interpretation

#### Hypothesis C: Hardcoded in Claude Code
- **If true**: Requires Claude Code update (out of our control) ❌
- **Evidence needed**: Check Claude Code source or documentation

---

### Validation Test

**Before reorganizing, run this test**:

```bash
# Step 1: Create nested test skill
mkdir -p .claude/skills/test-nested/test-discovery
cat > .claude/skills/test-nested/test-discovery/SKILL.md <<EOF
---
name: test-discovery
description: Test if nested skills are discovered
---

This is a test skill to validate discovery mechanism.
EOF

# Step 2: Invoke Claude in fresh session
# Ask Claude to apply test-discovery skill
# OR check if skill appears in available skills

# Step 3: Observe
# - If skill discovered → Recursive discovery ✅ (safe to reorganize)
# - If skill NOT discovered → One-level discovery ❌ (reorganization breaks)

# Step 4: Cleanup
rm -rf .claude/skills/test-nested
```

**Critical**: DO NOT reorganize until this test confirms recursive discovery.

---

## Recommendation

### Decision: ⚠️ **NO** (Not Now - Wait and See)

**Rationale**:

1. **Unknown discovery mechanism** (HIGH RISK)
   - We don't know if Claude Code supports nested skills
   - Reorganizing could break entire skill system
   - Risk mitigation: Test discovery first

2. **Premature optimization** (YAGNI violation)
   - Only 9 skills currently (flat structure works fine)
   - Threshold for reorganization: ~15 skills
   - Time to threshold: ~6 months
   - No pressing need to reorganize now

3. **Non-trivial migration cost**
   - 22 files with hardcoded paths to update
   - Risk of breaking references
   - 1-2 hours work + testing
   - Benefit doesn't justify cost yet

4. **Type classification not binary**
   - Hybrid skills exist (error-investigation)
   - Forcing binary choice creates ambiguity
   - Metadata approach better captures nuance

---

### Alternative Recommendation: **Metadata Now, Reorganize Later**

**Phase 1 (Now)**: Add type metadata to SKILL.md

```yaml
---
name: research
type: generalized
scope: "Systematic investigation methodology for any problem"
applies_to: "Any problem requiring root cause analysis"
---
```

**Benefits**:
- ✅ Type documented without path changes
- ✅ No discovery risk
- ✅ No reference updates needed
- ✅ Preserves option to reorganize later

**Phase 2 (At 15+ skills)**: Consider nested structure

**Conditions for reorganization**:
- [ ] Skill count reaches 15+ (current: 9)
- [ ] Discovery mechanism validated (recursive glob confirmed)
- [ ] Team agrees nested structure adds value
- [ ] Migration plan created (update all 22+ references)

---

## Action Items

### Immediate (This Week)
- [x] Create abstraction document on skill types
- [ ] Add `type` field to all SKILL.md frontmatter
- [ ] Document skill types in `.claude/skills/README.md`
- [ ] Update CLAUDE.md with skill type principle

### Validation (Before Any Reorganization)
- [ ] Test nested skill discovery (see validation test above)
- [ ] Document discovery mechanism findings
- [ ] If non-recursive: Contact Claude Code team about support

### Future (At 15+ skills)
- [ ] Re-evaluate folder structure
- [ ] If reorganizing: Update all 22+ references
- [ ] If reorganizing: Test discovery thoroughly
- [ ] If reorganizing: Create migration guide

---

## Follow-Up

### Journal This Decision
```bash
/journal architecture "Why skills remain flat structure for now"
```

**Capture**:
- Current scale (9 skills) doesn't justify reorganization
- Discovery mechanism unknown (risk too high)
- YAGNI principle: reorganize when needed (15+ skills)
- Metadata approach captures type distinction without path changes

---

### Proof (If Needed)
```bash
/proof "Nested skill structure works with Claude Code auto-discovery"
```

**Derive from**:
- Claude Code discovery mechanism
- File system structure requirements
- Skill registration patterns

---

### Validate Assumptions
```bash
/validate "Claude Code discovers skills recursively"
```

**Check**:
- Create nested test skill
- Verify Claude can find it
- Document discovery pattern

---

## Conclusion

**Status**: ⚠️ **DEFER REORGANIZATION**

**Key insights**:
1. **Discovery risk is too high** (unknown if nested skills work)
2. **Scale doesn't justify change yet** (9 skills manageable flat)
3. **Type distinction can be captured via metadata** (no structure change needed)
4. **Reorganize later if needed** (at 15+ skills, after validating discovery)

**Recommended approach**:
- **Now**: Add type metadata to SKILL.md (safe, low-cost)
- **At 15+ skills**: Re-evaluate nested structure (if discovery validated)
- **Never**: Reorganize without validating discovery mechanism first

**This what-if revealed**: The architectural distinction (generalized vs domain-specific) is real and valuable, but **making it visible in folder structure** is premature optimization at current scale. Metadata-only approach captures the distinction without the risks.

---

## Metadata

**Assumption Type**: Architecture (folder structure reorganization)
**Decision**: NO (not now)
**Confidence**: High (based on scale, risk, and YAGNI principle)
**Revisit At**: 15+ skills (~6 months from now)
**Created**: 2025-12-25
