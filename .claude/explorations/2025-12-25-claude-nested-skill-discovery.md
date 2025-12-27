# Exploration: How to Determine if Claude Code Supports Nested Skill Structures

**Date**: 2025-12-25
**Focus**: Comprehensive (need definitive answer)
**Status**: Complete

---

## Problem Decomposition

**Goal**: Figure out if Claude Code supports nested skill structures

### Core Requirements

**What MUST we determine**:
- ✅ Does Claude Code discover skills in nested directories?
- ✅ What is the exact glob pattern used for discovery?
- ✅ Is discovery recursive or one-level only?
- ✅ Can we reorganize `.claude/skills/` safely?

**Non-negotiable**:
- Must not break existing skills during investigation
- Must provide definitive answer (not speculation)
- Must be testable in current environment

### Constraints

**Technical**:
- Cannot modify Claude Code source (closed-source)
- Cannot ask Anthropic directly (async, slow)
- Must test in current project environment

**Time**:
- Need answer before making reorganization decision
- Should complete investigation in < 1 hour

**Risk**:
- Cannot break production skills
- Must be reversible (test, then cleanup)

### Success Criteria

**We have succeeded when**:
- [ ] Definitive answer: Nested skills work? (YES/NO)
- [ ] Discovery pattern documented (exact glob pattern)
- [ ] Test case validates answer (empirical evidence)
- [ ] Safe to proceed with reorganization decision

### Stakeholders

**Who cares**:
- **Architect** (me): Need to decide on folder reorganization
- **Claude Code system**: Auto-discovery must continue working
- **Future maintainers**: Need to know constraints

---

## Solution Space (Divergent Phase)

### Option 1: Empirical Test (Create Nested Skill)

**Description**: Create a test skill in nested directory and see if Claude discovers it

**How it works**:
```bash
# Create nested test skill
mkdir -p .claude/skills/test-category/test-nested-skill
cat > .claude/skills/test-category/test-nested-skill/SKILL.md <<EOF
---
name: test-nested-discovery
description: Test if nested skills are discovered
---

# Test Nested Skill Discovery

This is a test skill in a nested directory.
If Claude can discover this, nested structures are supported.
EOF

# Test discovery
# Method A: Ask Claude to list available skills
# Method B: Invoke test skill explicitly
# Method C: Check if skill appears in Claude's context

# Cleanup after test
rm -rf .claude/skills/test-category
```

**Pros**:
- ✅ Direct empirical evidence (tests actual behavior)
- ✅ Definitive answer (works or doesn't work)
- ✅ Low risk (easy to cleanup)
- ✅ Fast (< 5 minutes to execute)

**Cons**:
- ❌ Requires manual intervention (ask Claude to test)
- ❌ May not reveal exact discovery pattern
- ❌ Relies on observable behavior, not source code

**Examples**:
- Standard testing approach for black-box systems
- How we discovered other Claude Code behaviors

**Resources**:
- Test script already written in what-if analysis
- Can execute immediately

---

### Option 2: Documentation Search

**Description**: Search official Claude Code documentation for skill discovery pattern

**How it works**:
```bash
# Search local Claude Code documentation
claude --help | grep -i skill
claude help skills

# Search online documentation
# - https://claude.com/docs (if exists)
# - https://support.claude.com (help articles)
# - GitHub discussions, if Claude Code is open source
```

**Pros**:
- ✅ Authoritative answer (if documented)
- ✅ May reveal implementation details
- ✅ No risk to existing skills

**Cons**:
- ❌ May not be documented (common for implementation details)
- ❌ Documentation may be outdated
- ❌ Assumes documentation exists and is accurate

**Examples**:
- How we learned about command YAML frontmatter
- How we understood skill system initially

**Resources**:
- `claude --help` output
- Claude Code online docs
- Support articles

---

### Option 3: Source Code Inspection

**Description**: Inspect Claude Code source code for skill discovery implementation

**How it works**:
```bash
# If Claude Code is open source
git clone https://github.com/anthropics/claude-code
grep -r "skills" src/
grep -r "glob\|discover" src/

# If Claude Code is closed source
# - Decompile/reverse engineer (unethical, TOS violation)
# - OR: This option is not viable
```

**Pros**:
- ✅ Authoritative answer (source of truth)
- ✅ Reveals exact implementation
- ✅ Shows ALL discovery patterns

**Cons**:
- ❌ Requires Claude Code to be open source (unknown)
- ❌ Reverse engineering is unethical/illegal
- ❌ May violate terms of service

**Examples**:
- How we inspect our own codebase
- Standard approach for open-source tools

**Resources**:
- Claude Code repository (if public)
- Decompilation tools (NOT RECOMMENDED)

---

### Option 4: File System Monitoring

**Description**: Monitor file system access to see what Claude Code reads during startup

**How it works**:
```bash
# Use strace (Linux) or similar to monitor file access
strace -e openat,stat claude 2>&1 | grep -i skill

# Look for patterns like:
# - openat(".claude/skills/code-review/SKILL.md")
# - stat(".claude/skills/*/SKILL.md")  # One-level glob
# - stat(".claude/skills/**/SKILL.md") # Recursive glob

# Analysis reveals glob pattern used
```

**Pros**:
- ✅ Empirical evidence of actual behavior
- ✅ Shows exact file access patterns
- ✅ Works regardless of documentation

**Cons**:
- ❌ Requires system-level tools (strace, dtrace)
- ❌ May produce massive output (hard to parse)
- ❌ May not work in containerized environments
- ❌ Requires technical expertise to interpret

**Examples**:
- How we debug file access issues
- Standard approach for reverse-engineering behavior

**Resources**:
- `strace` (Linux)
- `fs_usage` (macOS)
- `procmon` (Windows)

---

### Option 5: Community Knowledge

**Description**: Search community discussions, GitHub issues, Discord for answers

**How it works**:
```bash
# Search GitHub Issues (if Claude Code has public repo)
# https://github.com/anthropics/claude-code/issues?q=nested+skills

# Search Reddit
# r/ClaudeAI or similar

# Search Discord
# Anthropic Discord server (if exists)

# Search Twitter/X
# @AnthropicAI mentions
```

**Pros**:
- ✅ May find answer from others who tested
- ✅ Community knowledge aggregates experience
- ✅ No risk to our environment

**Cons**:
- ❌ May not exist (if no one else asked)
- ❌ Information may be outdated
- ❌ Requires time to search multiple sources
- ❌ Answer may be speculation, not fact

**Examples**:
- How we learned about Skills vs MCP distinction
- How we found browser-use skill

**Resources**:
- GitHub Issues/Discussions
- Reddit communities
- Discord servers
- Twitter/X

---

### Option 6: Incremental Migration Test

**Description**: Gradually migrate one skill to nested structure and monitor for breakage

**How it works**:
```bash
# Step 1: Create nested directory
mkdir -p .claude/skills/domain-specific

# Step 2: Move ONE skill (least critical)
mv .claude/skills/line-uiux .claude/skills/domain-specific/line-uiux

# Step 3: Test if skill still works
# - Ask Claude to apply LINE Bot patterns
# - Check if skill auto-discovered

# Step 4: If works → nested supported ✅
# Step 5: If breaks → revert immediately ❌
mv .claude/skills/domain-specific/line-uiux .claude/skills/line-uiux
```

**Pros**:
- ✅ Real-world test (production-like)
- ✅ Tests actual use case (our reorganization)
- ✅ Easy to revert (one skill only)

**Cons**:
- ❌ Temporarily breaks skill (if nested not supported)
- ❌ May affect Claude's performance during test
- ❌ Riskier than isolated test (affects real skill)

**Examples**:
- Blue-green deployment testing
- Canary releases

**Resources**:
- Git for version control (revert if needed)
- Existing skills as test subjects

---

### Option 7: Ask Claude Directly (Meta)

**Description**: Ask Claude (current session) if it knows how skill discovery works

**How it works**:
```bash
# Simply ask Claude:
# "Do you know what glob pattern Claude Code uses to discover skills?"
# "Can you read skills in nested directories like .claude/skills/category/skill/?"

# Analyze response:
# - If Claude knows → Likely documented in its training data
# - If Claude doesn't know → Need empirical test
```

**Pros**:
- ✅ Immediate answer (no setup needed)
- ✅ May have access to training data we don't
- ✅ Zero risk to environment

**Cons**:
- ❌ May not have access to implementation details
- ❌ Claude's knowledge cutoff (may be outdated)
- ❌ Cannot verify answer empirically (trust, not proof)

**Examples**:
- How we ask conceptual questions
- How we leverage Claude's knowledge base

**Resources**:
- Current Claude session
- Claude's training data (implicit)

---

## Evaluation Matrix

**Focus**: Comprehensive (need definitive answer with minimal risk)

| Criterion | Empirical Test | Documentation | Source Code | FS Monitor | Community | Migration Test | Ask Claude |
|-----------|----------------|---------------|-------------|------------|-----------|----------------|------------|
| **Reliability** | 9/10 | 8/10 | 10/10 | 9/10 | 5/10 | 8/10 | 6/10 |
| **Speed** | 9/10 | 7/10 | 3/10 | 5/10 | 4/10 | 7/10 | 10/10 |
| **Risk** | 9/10 | 10/10 | 0/10 | 8/10 | 10/10 | 6/10 | 10/10 |
| **Definitiveness** | 9/10 | 9/10 | 10/10 | 8/10 | 4/10 | 8/10 | 5/10 |
| **Effort** | 9/10 | 8/10 | 2/10 | 4/10 | 5/10 | 7/10 | 10/10 |
| **Total** | **45/50** | **42/50** | **25/50** | **34/50** | **28/50** | **36/50** | **41/50** |

### Scoring Rationale

**Empirical Test (45/50)** ⭐ Winner
- **Reliability (9/10)**: Direct test of actual behavior (not speculation)
- **Speed (9/10)**: < 5 minutes to create, test, cleanup
- **Risk (9/10)**: Isolated test, easy cleanup, no production impact
- **Definitiveness (9/10)**: Binary answer (works or doesn't)
- **Effort (9/10)**: Simple shell commands, minimal setup

**Documentation Search (42/50)** - Strong second
- **Reliability (8/10)**: Authoritative if exists, but may not exist
- **Speed (7/10)**: Search takes time, may require web search
- **Risk (10/10)**: Zero risk (read-only)
- **Definitiveness (9/10)**: Authoritative if found
- **Effort (8/10)**: Simple search, but multiple sources

**Ask Claude (41/50)** - Fast but less definitive
- **Reliability (6/10)**: Depends on training data, may be outdated
- **Speed (10/10)**: Immediate answer
- **Risk (10/10)**: Zero risk
- **Definitiveness (5/10)**: Cannot verify empirically
- **Effort (10/10)**: Just ask a question

**Migration Test (36/50)**
- **Risk (6/10)**: Temporarily breaks real skill (not isolated)
- **Definitiveness (8/10)**: Tests exact use case, but higher risk

**File System Monitor (34/50)**
- **Effort (4/10)**: Requires strace, parsing massive output
- **Speed (5/10)**: Setup + execution + analysis = 30+ minutes

**Community Knowledge (28/50)**
- **Reliability (5/10)**: May not exist or be speculation
- **Definitiveness (4/10)**: Unverified claims

**Source Code Inspection (25/50)**
- **Risk (0/10)**: Unethical if closed-source (reverse engineering)
- **Effort (2/10)**: Requires source access we don't have

---

## Ranked Recommendations

### 1. Hybrid Approach: Ask Claude → Empirical Test → Documentation (Score: Combined)

**Strategy**: Use multiple approaches in sequence for best confidence

**Phase 1: Ask Claude (30 seconds)**
```bash
# Simply ask current Claude session
"Do you know if Claude Code discovers skills recursively in nested directories?"
```

**Phase 2: Empirical Test (5 minutes)**
```bash
# Create nested test skill
mkdir -p .claude/skills/test-category/test-nested-skill
cat > .claude/skills/test-category/test-nested-skill/SKILL.md <<EOF
---
name: test-nested-discovery
description: Test nested skill discovery
---
This tests if Claude Code supports nested skill structures.
EOF

# Test discovery (ask Claude to list skills or invoke test skill)

# Cleanup
rm -rf .claude/skills/test-category
```

**Phase 3: Documentation Verification (5 minutes)**
```bash
# Search for official documentation
claude --help | grep -i skill
# Check online docs: support.claude.com
```

**Why hybrid**:
- ✅ Fast initial answer (Ask Claude)
- ✅ Empirical validation (Test confirms)
- ✅ Authoritative backup (Docs verify)
- ✅ Triple-check (high confidence)

**Total time**: ~10 minutes
**Confidence**: Very High (3 independent sources)

---

### 2. Empirical Test Only (Score: 45/50)

**When to choose**: Need fast, definitive answer

**Implementation**:
```bash
#!/bin/bash

echo "======================================================"
echo "Testing Claude Code Nested Skill Discovery"
echo "======================================================"
echo ""

# Step 1: Create nested test skill
echo "[1/4] Creating nested test skill..."
mkdir -p .claude/skills/test-category/test-nested-skill
cat > .claude/skills/test-category/test-nested-skill/SKILL.md <<'EOF'
---
name: test-nested-discovery
description: Test if nested skills are discovered by Claude Code
---

# Test Nested Skill Discovery

This is a test skill located at:
`.claude/skills/test-category/test-nested-skill/SKILL.md`

If Claude Code can discover this skill, then nested structures are supported.

## Test Method

Ask Claude: "Can you see the test-nested-discovery skill?"

## Expected Results

- **If discovered**: Claude confirms it can see this skill → Nested supported ✅
- **If not discovered**: Claude cannot find skill → Flat structure only ❌
EOF

echo "✅ Created: .claude/skills/test-category/test-nested-skill/SKILL.md"
echo ""

# Step 2: Verify file exists
echo "[2/4] Verifying test skill file..."
if [ -f ".claude/skills/test-category/test-nested-skill/SKILL.md" ]; then
  echo "✅ Test skill file exists"
else
  echo "❌ Test skill file not found!"
  exit 1
fi
echo ""

# Step 3: Instructions for manual test
echo "[3/4] Manual Test Required"
echo "======================================================"
echo ""
echo "Please ask Claude (in a NEW session):"
echo ""
echo '  "Can you see the test-nested-discovery skill?"'
echo ""
echo "OR"
echo ""
echo '  "List all available skills"'
echo ""
echo "======================================================"
echo ""
echo "Results:"
echo "  - If Claude can see/list this skill → Nested supported ✅"
echo "  - If Claude cannot find this skill → Flat only ❌"
echo ""

# Step 4: Cleanup prompt
echo "[4/4] Cleanup"
echo "======================================================"
echo ""
echo "After testing, run:"
echo ""
echo "  rm -rf .claude/skills/test-category"
echo ""
echo "To remove the test skill."
echo ""
echo "======================================================"
```

**Trade-offs**:
- **Gain**: Fast, definitive, low-risk
- **Lose**: Requires manual test (ask Claude in new session)

**Next step**: Execute test script above

---

### 3. Documentation Search (Score: 42/50)

**When to choose**: Want authoritative source without testing

**Implementation**:
```bash
# Local help
claude --help | grep -i skill
claude help skills 2>/dev/null

# Online documentation
# - Visit: https://support.claude.com
# - Search: "skill discovery" or "nested skills"
# - Check: Claude Code documentation section

# GitHub (if public repo)
# - Visit: https://github.com/anthropics/claude-code
# - Search issues: "nested skills" or "skill structure"
```

**Trade-offs**:
- **Gain**: No risk, authoritative if found
- **Lose**: May not exist, slower than empirical test

---

### 4. Ask Claude Meta (Score: 41/50)

**When to choose**: Want instant answer before investing in test

**Implementation**:
```
"Do you know if Claude Code discovers skills recursively in nested directories?
For example, would a skill at `.claude/skills/category/skill-name/SKILL.md` be discovered?
Or does discovery only work at `.claude/skills/skill-name/SKILL.md`?"
```

**Trade-offs**:
- **Gain**: Instant answer, zero setup
- **Lose**: Less definitive, cannot verify empirically

**Use as**: Phase 1 of hybrid approach (quick check before test)

---

## Resources Gathered

### Official Documentation

**Claude Code CLI**:
- Local: `claude --help` (check for skill-related options)
- Online: https://support.claude.com (search for "skills")

**Skills Documentation**:
- [What are Skills? - Claude Help Center](https://support.claude.com/en/articles/12512176-what-are-skills)
- Installation and discovery patterns

### Community Knowledge

**GitHub** (if public repo):
- https://github.com/anthropics/claude-code
- Search issues: "nested skills", "skill discovery", "skill structure"

**Community Discussions**:
- r/ClaudeAI on Reddit
- Anthropic Discord (if exists)
- Twitter/X: @AnthropicAI

### Technical References

**File System Glob Patterns**:
- `*` - One-level wildcard (`.claude/skills/*/SKILL.md`)
- `**` - Recursive wildcard (`.claude/skills/**/SKILL.md`)

**Testing Approaches**:
- Black-box testing (external behavior)
- File system monitoring (strace, fs_usage)
- Canary testing (incremental migration)

---

## Next Steps

### Immediate Action: Execute Hybrid Approach

**Step 1: Ask Claude (Now)**
```
"Do you know if Claude Code discovers skills recursively in nested directories?"
```

**Expected outcome**:
- If YES → Proceed to empirical test for validation
- If NO → Empirical test is critical (only way to know)
- If UNCERTAIN → Empirical test required

---

**Step 2: Empirical Test (5 minutes)**
```bash
# Run test script
./test-nested-skill-discovery.sh

# OR manual test
mkdir -p .claude/skills/test-category/test-nested-skill
echo "---
name: test-nested-discovery
---
Test nested skill" > .claude/skills/test-category/test-nested-skill/SKILL.md

# Ask Claude in NEW session: "Can you see test-nested-discovery skill?"

# Cleanup
rm -rf .claude/skills/test-category
```

**Expected outcome**:
- Discovered → Nested supported ✅ (safe to reorganize)
- Not discovered → Flat only ❌ (reorganization breaks)

---

**Step 3: Document Findings**

If nested supported:
```bash
/journal architecture "Claude Code supports nested skill discovery"
# Update what-if analysis with confirmed answer
```

If flat only:
```bash
/journal architecture "Claude Code requires flat skill structure"
# Update CLAUDE.md with constraint
```

---

**Step 4: Make Reorganization Decision**

```bash
# If nested supported
/specify "Reorganize skills by type (generalized vs domain-specific)"

# If flat only
/specify "Add type metadata to SKILL.md frontmatter (no reorganization)"
```

---

## Alternative Paths

### If Empirical Test Inconclusive

**Scenario**: Test skill exists but unclear if discovered

**Next step**:
```bash
# More explicit test
# Create skill with unique invocation trigger
# Ask Claude to perform task that ONLY test skill knows about
```

### If Documentation Found First

**Scenario**: Found authoritative docs saying "recursive supported"

**Next step**:
```bash
# Still run empirical test (validate docs are correct)
# Docs may be outdated or incorrect
```

### If Claude Says "Don't Know"

**Scenario**: Claude cannot answer (no training data)

**Next step**:
```bash
# Empirical test is only option
# Proceed with test script
```

---

## Success Criteria Checklist

After completing investigation:

- [ ] **Definitive answer obtained**: Nested works? (YES/NO)
- [ ] **Evidence type documented**: (Empirical | Documentation | Both)
- [ ] **Test case executed**: (if empirical approach used)
- [ ] **Findings journaled**: Decision recorded in architecture journal
- [ ] **Reorganization decision made**: (Proceed | Defer | Metadata-only)

---

## Conclusion

**Recommended approach**: **Hybrid (Ask Claude → Empirical Test → Documentation)**

**Rationale**:
1. **Fast initial check** (Ask Claude - 30 seconds)
2. **Empirical validation** (Test - 5 minutes)
3. **Authoritative backup** (Docs - 5 minutes if found)

**Total time**: ~10 minutes
**Confidence**: Very High (triple verification)
**Risk**: Minimal (isolated test, easy cleanup)

**This exploration revealed**:
- Multiple viable approaches exist (7 options)
- Empirical test is most reliable (45/50 score)
- Hybrid approach gives highest confidence (combines top 3)
- Answer is obtainable in < 10 minutes (not speculative)

**Next action**: Execute Step 1 (Ask Claude) immediately to start the investigation.

---

## Metadata

**Exploration Type**: Technical investigation
**Options Explored**: 7 approaches
**Top Recommendation**: Hybrid (Ask + Test + Docs)
**Time to Answer**: ~10 minutes
**Confidence**: Very High (empirical + authoritative sources)
**Created**: 2025-12-25
