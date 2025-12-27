# Architecture Pattern: Two Types of Skills

**Pattern Type**: Architecture (skill taxonomy)
**Date**: 2025-12-25
**Confidence**: High (derived from conceptual analysis + empirical examples)
**Instances**: Multiple existing skills analyzed

---

## Pattern Description

**What it is**: Skills fall into two fundamentally different categories based on their scope and applicability.

**Core Distinction**:
```
Type 1: Generalized Skills
  "Step to think/do X for all X"
  Example: "How to find bugs" (works for ANY bug)

Type 2: Domain-Specific Skills
  "Step to do Y, only Y"
  Example: "How to interact with browser" (ONLY for browsers)
```

**Why it matters**: Understanding this distinction determines:
- Where to apply each skill
- How to compose skills
- When to create new skills vs extending existing ones

---

## Concrete Instances

### Type 1: Generalized Skills (Process/Methodology)

#### Instance 1: bug-hunt (Generalized Debugging)
**Scope**: ANY bug in ANY system
**Pattern**: Systematic investigation methodology
```markdown
Apply to:
- Lambda timeout bugs
- UI rendering bugs
- Database migration bugs
- Network connectivity bugs
- Type system bugs

The PROCESS is generalized, instances are specific.
```

#### Instance 2: research (Generalized Investigation)
**Scope**: ANY problem requiring root cause analysis
**Pattern**: Multi-layer verification framework
```markdown
Apply to:
- API failures
- Performance degradation
- Configuration issues
- Integration problems

The METHODOLOGY is generalized, domains vary.
```

#### Instance 3: refactor (Generalized Code Improvement)
**Scope**: ANY code that needs improvement
**Pattern**: Complexity analysis + hotspot detection
```markdown
Apply to:
- Python services
- TypeScript frontend
- Terraform infrastructure
- Shell scripts

The APPROACH is generalized, languages differ.
```

#### Instance 4: testing-workflow (Generalized Test Patterns)
**Scope**: ANY testing scenario
**Pattern**: Test tiers + anti-patterns + defensive principles
```markdown
Apply to:
- Unit tests
- Integration tests
- E2E tests
- Infrastructure tests

The PRINCIPLES are generalized, implementations vary.
```

---

### Type 2: Domain-Specific Skills (Domain/Tool Expertise)

#### Instance 1: browser-use (Browser Automation Only)
**Scope**: ONLY browser interactions
**Pattern**: Browser-specific workflow orchestration
```markdown
Apply to:
- Navigate web pages
- Fill forms
- Click elements
- Wait for page loads

Does NOT apply to:
- API debugging
- Database queries
- File system operations
```

#### Instance 2: line-uiux (LINE Bot UI Patterns Only)
**Scope**: ONLY LINE Bot chat interfaces
**Pattern**: LINE-specific UX conventions
```markdown
Apply to:
- LINE message formatting
- LINE rich menus
- LINE flex messages

Does NOT apply to:
- Telegram Mini Apps
- Web dashboards
- REST APIs
```

#### Instance 3: telegram-uiux (Telegram Mini App Only)
**Scope**: ONLY Telegram Mini App frontend
**Pattern**: Telegram-specific React patterns
```markdown
Apply to:
- Telegram WebApp SDK
- Telegram UI/UX patterns
- Telegram state management

Does NOT apply to:
- LINE Bot
- Standalone web apps
- Mobile native apps
```

#### Instance 4: database-migration (Database Schema Only)
**Scope**: ONLY database schema evolution
**Pattern**: Aurora MySQL migration patterns
```markdown
Apply to:
- Schema changes
- Data migrations
- MySQL-specific gotchas

Does NOT apply to:
- NoSQL migrations
- API versioning
- Infrastructure changes
```

#### Instance 5: deployment (Deployment Process Only)
**Scope**: ONLY serverless AWS Lambda deployment
**Pattern**: Zero-downtime Lambda deployment
```markdown
Apply to:
- Lambda deployments
- ECR image promotion
- Alias management

Does NOT apply to:
- Database deployments
- Frontend deployments (different pattern)
- Infrastructure provisioning
```

---

## Generalized Pattern

### Type 1: Generalized Skills (Methodology)

**Signature** (how to recognize):
- Skill name is a **verb** (bug-hunt, research, refactor, validate)
- Applicable across **multiple domains**
- Describes a **process/methodology**, not a tool
- Can be applied to problems you haven't seen before

**Characteristics**:
- **Horizontal**: Cuts across multiple domains
- **Process-oriented**: Defines steps/phases/framework
- **Context-independent**: Works regardless of technology stack
- **Parametric**: Takes problem as input, applies process

**Template Structure**:
```markdown
skill/
├── SKILL.md            # Methodology overview
├── METHODOLOGY.md      # Step-by-step process
├── PATTERNS.md         # Common patterns within methodology
└── ANTI-PATTERNS.md    # Common mistakes to avoid

Focus: HOW to approach problems (the thinking process)
```

**Examples**:
- `/bug-hunt` - How to find bugs (any bug)
- `/research` - How to investigate (any problem)
- `/refactor` - How to improve code (any codebase)
- `/validate` - How to verify claims (any hypothesis)
- `/decompose` - How to break down problems (any complexity)

**Value Proposition**: Reusable across many contexts

---

### Type 2: Domain-Specific Skills (Domain Expertise)

**Signature** (how to recognize):
- Skill name is a **noun/domain** (browser-use, database-migration, line-uiux)
- Applicable to **one specific domain** only
- Describes **tool-specific knowledge**, not universal process
- Requires domain context to be useful

**Characteristics**:
- **Vertical**: Deep into one domain
- **Tool-oriented**: Specific technology/platform/system
- **Context-dependent**: Only works in specific environment
- **Specialized**: Expert knowledge for that domain

**Template Structure**:
```markdown
skill/
├── SKILL.md                # Domain overview
├── WORKFLOWS.md            # Domain-specific workflows
├── GOTCHAS.md             # Domain-specific pitfalls
└── REFERENCE.md           # Domain-specific commands/APIs

Focus: WHAT to do in this specific domain
```

**Examples**:
- `browser-use` - How to automate browsers (only browsers)
- `line-uiux` - LINE Bot patterns (only LINE)
- `telegram-uiux` - Telegram Mini App (only Telegram)
- `database-migration` - Schema evolution (only databases)
- `deployment` - Lambda deployment (only serverless)

**Value Proposition**: Deep expertise in specific domain

---

## The Composition Pattern

### Skills Compose Hierarchically

```
Generalized Skill (Methodology)
    ↓ (applies process to domain)
Domain-Specific Skill (Domain Expertise)
    ↓ (uses tools)
MCP Tools (Connectivity)
    ↓ (access)
External System
```

**Example 1: Debugging a Browser Issue**
```
/bug-hunt (generalized debugging methodology)
    ↓ applies to
browser-use skill (browser domain expertise)
    ↓ uses
Browser MCP tools (connectivity to Chrome/Firefox)
    ↓ access
Browser instance
```

**Example 2: Investigating Database Performance**
```
/research (generalized investigation methodology)
    ↓ applies to
database-migration skill (database domain expertise)
    ↓ uses
AWS MCP tools (connectivity to RDS)
    ↓ access
Aurora database
```

**Example 3: Refactoring Frontend Code**
```
/refactor (generalized code improvement methodology)
    ↓ applies to
telegram-uiux skill (Telegram frontend domain expertise)
    ↓ reads
TypeScript/React codebase (no MCP needed, direct file access)
```

---

## Decision Tree: Which Type of Skill?

### When to Create Generalized Skill

Create **Type 1: Generalized Skill** when:
- ✅ You've solved **similar problems in different domains**
- ✅ The **process** is reusable, even if domains differ
- ✅ You can describe steps **without mentioning specific tools**
- ✅ The methodology applies to **problems you haven't seen yet**

**Examples**:
- "How to debug performance issues" (works for backend, frontend, database)
- "How to validate hypotheses" (works for code, config, architecture)
- "How to plan complex changes" (works for features, refactors, migrations)

**Anti-pattern**: Don't create generalized skill for one-time use
```
❌ "How to deploy THIS specific Lambda function"
✅ "How to deploy serverless functions" (generalized)
```

---

### When to Create Domain-Specific Skill

Create **Type 2: Domain-Specific Skill** when:
- ✅ You need **deep expertise in one specific domain**
- ✅ The domain has **unique patterns/gotchas** not shared elsewhere
- ✅ You reference **specific tools/APIs/conventions** frequently
- ✅ The knowledge **doesn't transfer** to other domains

**Examples**:
- "LINE Bot UX conventions" (only LINE, doesn't apply to Telegram)
- "Aurora MySQL migration gotchas" (only MySQL, doesn't apply to Postgres)
- "Browser automation workflows" (only browsers, doesn't apply to APIs)

**Anti-pattern**: Don't create domain-specific skill that's too narrow
```
❌ "How to click login button on example.com"
✅ "How to automate browser interactions" (broader domain)
```

---

### The Hybrid Case: Specialized Methodology

Some skills are **generalized methodologies for specific domains**:

**Example**: `error-investigation` skill
```
Type: Hybrid (Generalized methodology + AWS domain)

Generalized part:
- Multi-layer verification framework
- Systematic debugging approach
- Failure mode analysis

Domain-specific part:
- AWS-specific layers (Lambda, CloudWatch, VPC)
- AWS CLI commands
- AWS-specific gotchas
```

**When to use hybrid**:
- Methodology is generalized (debugging approach)
- Domain is specific (AWS infrastructure)
- Pattern: "Generalized methodology applied to specific domain"

---

## Impact on Skill Organization

### Current Skill Inventory Analysis

**Generalized Skills (Methodology)** ✅:
```
.claude/skills/
├── research/              # Systematic investigation (any problem)
├── refactor/              # Code improvement (any code)
├── testing-workflow/      # Test patterns (any tests)
├── code-review/           # Code review (any code)
└── [future: bug-hunt, validate, decompose, etc.]
```

**Domain-Specific Skills (Domain Expertise)** ✅:
```
.claude/skills/
├── line-uiux/             # LINE Bot patterns (only LINE)
├── telegram-uiux/         # Telegram Mini App (only Telegram)
├── database-migration/    # Schema evolution (only databases)
├── deployment/            # Lambda deployment (only serverless)
└── error-investigation/   # AWS debugging (only AWS)
```

**Observation**: Current skills correctly follow this pattern!

---

### Naming Convention Recommendation

**Type 1: Generalized Skills**
- Use **verb** or **process** names
- Examples: `bug-hunt`, `research`, `refactor`, `validate`, `decompose`
- Indicates: "This is a HOW (methodology)"

**Type 2: Domain-Specific Skills**
- Use **noun** or **domain** names
- Examples: `browser-use`, `line-uiux`, `database-migration`
- Indicates: "This is a WHAT (domain expertise)"

**Hybrid Skills**
- Use **domain + verb** names
- Examples: `error-investigation` (AWS + investigating)
- Indicates: "This is HOW for specific WHAT"

---

## Composition Examples

### Example 1: Debugging a Production Issue

**User invokes**: `/bug-hunt "Lambda timeout in production"`

**Execution**:
1. **Generalized skill activated**: `research` (systematic investigation)
2. **Detects domain**: AWS Lambda (infrastructure)
3. **Loads domain skill**: `error-investigation` (AWS debugging patterns)
4. **Uses domain knowledge**:
   - Check CloudWatch logs (AWS-specific)
   - Verify Lambda timeout settings (AWS-specific)
   - Check VPC networking (AWS-specific)
5. **Uses MCP tools**: AWS MCP (connectivity to CloudWatch, Lambda)

**Result**: Generalized methodology + domain expertise + tooling

---

### Example 2: Refactoring Frontend Component

**User invokes**: `/refactor "Telegram Mini App chart component"`

**Execution**:
1. **Generalized skill activated**: `refactor` (code improvement methodology)
2. **Detects domain**: Telegram Mini App (frontend)
3. **Loads domain skill**: `telegram-uiux` (Telegram patterns)
4. **Uses domain knowledge**:
   - Normalized state pattern (Telegram-specific)
   - Stale-while-revalidate (Telegram-specific)
   - Zustand state management (Telegram-specific)
5. **Uses file access**: Direct read (no MCP needed)

**Result**: Generalized methodology + domain expertise + direct file access

---

### Example 3: Creating Database Migration

**User invokes**: `/specify "Add user_facing_scores column to reports table"`

**Execution**:
1. **Generalized skill activated**: `specify` (design specification)
2. **Detects domain**: Database schema (Aurora MySQL)
3. **Loads domain skill**: `database-migration` (MySQL patterns)
4. **Uses domain knowledge**:
   - Reconciliation migration pattern (MySQL-specific)
   - CREATE TABLE IF NOT EXISTS gotchas (MySQL-specific)
   - ALTER TABLE MODIFY COLUMN data preservation (MySQL-specific)
5. **Uses MCP tools**: AWS MCP (connectivity to Aurora)

**Result**: Generalized methodology + domain expertise + tooling

---

## Trade-offs

### Generalized Skills (Type 1)

**Pros**:
- ✅ Reusable across many domains
- ✅ Builds transferable problem-solving skills
- ✅ Reduces duplication (one methodology, many applications)
- ✅ Easier to maintain (update methodology once)

**Cons**:
- ❌ May lack domain-specific nuance
- ❌ Requires domain skills to be fully effective
- ❌ Can be too abstract without concrete examples

**When to prefer**:
- You solve similar problems across domains frequently
- You want to teach **how to think** about problems
- You're building a general-purpose toolkit

---

### Domain-Specific Skills (Type 2)

**Pros**:
- ✅ Deep expertise in one area
- ✅ Captures domain-specific gotchas and patterns
- ✅ Immediately actionable (no abstraction needed)
- ✅ Easy to validate (test in specific domain)

**Cons**:
- ❌ Not reusable outside domain
- ❌ Can become outdated as tools evolve
- ❌ Proliferation (need many domain skills)

**When to prefer**:
- Domain has unique patterns not found elsewhere
- You work in this domain frequently
- Domain-specific gotchas are critical (e.g., MySQL ENUMs fail silently)

---

## Related Patterns

### MCP vs Domain-Specific Skills

**MCP** (Connectivity):
```
browser-mcp: "I can control browsers"
aws-mcp: "I can access AWS services"
github-mcp: "I can interact with GitHub"
```

**Domain-Specific Skills** (Expertise):
```
browser-use: "I know HOW to automate browser workflows"
error-investigation: "I know HOW to debug AWS issues"
deployment: "I know HOW to deploy to AWS Lambda"
```

**Pattern**: Domain skills **use** MCP tools but add **procedural knowledge**

---

### Commands vs Generalized Skills

**Commands** (User-invoked workflows):
```
/bug-hunt: User explicitly invokes debugging
/refactor: User explicitly requests refactoring
/validate: User explicitly asks for validation
```

**Generalized Skills** (Auto-discovered by Claude):
```
research skill: Claude auto-applies when investigating
code-review skill: Claude auto-applies when reviewing code
testing-workflow skill: Claude auto-applies when writing tests
```

**Pattern**: Commands **invoke** skills, skills provide methodology

---

## Graduation Path

### From Observation to Skill

**Type 1: Generalized Skill**
```
1. Observe: Solve similar problems in different domains (3+ times)
2. Abstract: Extract common methodology (/abstract)
3. Validate: Apply to new domain (test generalization)
4. Graduate: Create skill in .claude/skills/{verb}/
```

**Type 2: Domain-Specific Skill**
```
1. Observe: Encounter domain-specific patterns/gotchas (5+ times)
2. Document: Capture domain knowledge in journals
3. Validate: Verify patterns hold in domain
4. Graduate: Create skill in .claude/skills/{domain}/
```

---

## Action Items

- [x] Document skill type distinction in abstraction
- [ ] Review existing skills to confirm correct categorization
- [ ] Update skill creation guidelines to specify type
- [ ] Consider adding type metadata to SKILL.md frontmatter
- [ ] Create examples showing composition of both types

---

## Metadata

**Pattern Type**: Architecture (skill taxonomy)
**Confidence**: High
**Instances**: 9 existing skills analyzed
**Created**: 2025-12-25
**Impact**: Fundamental to skill system design

---

## Next Steps

### 1. Update Skill Documentation Template

Add type classification to SKILL.md frontmatter:
```yaml
---
name: skill-name
type: generalized | domain-specific | hybrid
scope:
  generalized: "What problems this methodology solves"
  domain-specific: "What domain this expertise covers"
---
```

### 2. Create Skill Creation Guideline

Document when to create each type:
- `.claude/guides/creating-skills.md`
- Include decision tree from this abstraction
- Add examples of good/bad skill boundaries

### 3. Validate Against Existing Skills

Audit current skills:
```bash
# Generalized (expected: verb names)
research, refactor, testing-workflow, code-review

# Domain-specific (expected: noun names)
line-uiux, telegram-uiux, database-migration, deployment, error-investigation

# Check for misclassified skills
```

### 4. Update CLAUDE.md

Add principle about skill types:
```markdown
## Skill System Principles

**Two Types of Skills**:
- **Generalized**: Methodology applicable across domains (verb names)
- **Domain-Specific**: Deep expertise in one domain (noun names)

**Composition**: Generalized skills apply methodologies to domain-specific expertise.
```

---

## Conclusion

**Key Insight**: Skills operate at two distinct levels of abstraction.

**Type 1: Generalized Skills** answer "HOW to approach problems" (methodology)
**Type 2: Domain-Specific Skills** answer "WHAT to do in this domain" (expertise)

**Value**: Understanding this distinction enables:
- ✅ Correct skill scoping (not too broad, not too narrow)
- ✅ Effective skill composition (methodology + domain + tools)
- ✅ Clear naming conventions (verbs vs nouns)
- ✅ Appropriate skill creation (when to generalize vs specialize)

**Impact**: This pattern is **foundational** to the skill system architecture and should inform all future skill creation.
