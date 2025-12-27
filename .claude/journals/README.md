# Journal Entries

Chronological log of decisions, solutions, patterns, and process improvements.

Journals capture knowledge **as it emerges** during development - before it becomes formal documentation. Think of journals as lightweight, fast decision logs that can later be extracted into ADRs, skills, or documentation.

---

## Categories

### `architecture/` - Design Decisions

**When to use**: Before making architectural choices, evaluating trade-offs

**Purpose**: Pre-ADR exploration - thinking through options before committing

**Template**: Context → Options → Decision → Consequences

**Example scenarios**:
- "Aurora vs DynamoDB for caching layer"
- "Serverless vs container deployment"
- "Monorepo vs multi-repo strategy"

**Graduation path**: Significant decisions → ADR (docs/adr/)

---

### `error/` - Bug Investigations & Solutions

**When to use**: After solving difficult bugs, production incidents

**Purpose**: Document investigation path, root cause, and prevention

**Template**: Symptoms → Investigation → Root Cause → Solution → Prevention

**Example scenarios**:
- "Lambda timeout during peak traffic"
- "MySQL connection pool exhaustion"
- "CloudFront cache poisoning incident"

**Graduation path**: Recurring patterns → error-investigation skill

---

### `pattern/` - Reusable Patterns

**When to use**: Discovering code or workflow patterns worth replicating

**Purpose**: Capture patterns before they're formalized in skills or docs

**Template**: Problem → Solution → When to Use → Trade-offs

**Example scenarios**:
- "Validation gates before workflow nodes"
- "Stale-while-revalidate for API caching"
- "Loud mock pattern for dev mocks"

**Graduation path**: Proven patterns → skill documentation or CODE_STYLE.md

---

### `meta/` - Process Improvements

**When to use**: Reflecting on development process, tooling, workflows

**Purpose**: Capture what's working and what needs improvement

**Template**: Observation → Analysis → Improvement → Action Items

**Example scenarios**:
- "Research-before-iteration saved 3 deploy cycles"
- "Hotspot analysis found 80% of bugs in 20% of files"
- "Test sabotage caught 5 non-failing tests"

**Graduation path**: Process changes → CLAUDE.md principles

---

## Journal Workflow

```
During development → Quick journal entry (2-5 min)
        ↓
Weekly review → Tag entries for graduation
        ↓
Graduation:
  - architecture → ADR (if significant)
  - error → skill pattern (if recurring)
  - pattern → skill documentation (if proven)
  - meta → CLAUDE.md update (if impactful)
```

**Key principle**: Journals are fast and informal. Don't over-think - just capture the decision while context is fresh.

---

## File Naming Convention

```
{category}/{YYYY-MM-DD}-{slug}.md
```

**Examples**:
- `architecture/2025-12-23-aurora-vs-dynamodb.md`
- `error/2025-12-22-lambda-timeout-production.md`
- `pattern/2025-12-21-validation-gates.md`
- `meta/2025-12-20-research-before-iteration.md`

**Slug rules**:
- Lowercase
- Hyphens separate words
- Alphanumeric only (no special chars)
- Descriptive but concise (3-8 words)

---

## Using `/journal` Command

```bash
# Create entry (opens editor)
/journal architecture "Aurora vs DynamoDB"

# Create entry with content
/journal error "Lambda timeout" "Occurred during peak traffic"

# Quick pattern capture
/journal pattern "Validation gates before workflows"

# Process reflection
/journal meta "Research saves deploy cycles"
```

See `.claude/commands/journal.md` for complete documentation.

---

## Recent Entries

<!-- Auto-updated by /journal command -->
<!-- Format: - [{date}] [{category}] [{title}](category/{filename}.md) -->

- [2025-12-24] [architecture] [Connascence as unified coupling framework - boundary principles and cohesion-coupling resolution](architecture/2025-12-24-connascence-as-unified-coupling-framework-boundary-principles-and-cohesion-coupling-resolution.md)

<!-- Example entries: -->
<!-- - [2025-12-23] [architecture] [Aurora caching strategy](architecture/2025-12-23-aurora-caching.md) -->
<!-- - [2025-12-22] [error] [Lambda cold start timeout](error/2025-12-22-lambda-timeout.md) -->

---

## Maintenance

### Weekly Review (Every Friday)

1. **Read** this week's journal entries
2. **Tag** entries for graduation:
   - `#to-adr` - Significant architectural decisions
   - `#to-skill` - Patterns worth formalizing
   - `#to-claude-md` - Process improvements
3. **Graduate** tagged entries to appropriate location
4. **Clean up** graduated entries (move to archive or delete)

### Monthly Evolution Review

Run `/evolve` to:
- Detect drift between journals and formal docs
- Identify undocumented patterns
- Suggest skill or CLAUDE.md updates

### Quarterly Archive

Move old entries (>90 days) to archive if not graduated:
```bash
mkdir -p .claude/journals/archive/{year}
mv .claude/journals/{category}/2025-01-*.md .claude/journals/archive/2025/
```

---

## Journal vs ADR vs Skill

| Aspect | Journal | ADR | Skill |
|--------|---------|-----|-------|
| **Speed** | Fast (2-5 min) | Slow (30-60 min) | Very slow (2-4 hours) |
| **Formality** | Informal | Formal | Very formal |
| **When** | During development | After decision committed | After pattern proven |
| **Audience** | Self | Team | Team + Future developers |
| **Change** | Can edit freely | Immutable once merged | Updated as patterns evolve |
| **Graduation** | To ADR or skill | N/A (final form) | N/A (living documentation) |

**Use case flow**:
```
Journal (quick capture)
    ↓ if significant
ADR (formal decision record)
    ↓ if recurring pattern
Skill (formalized expertise)
```

---

## Tips for Effective Journaling

### Do

- **Journal immediately** after solving or deciding
- **Be honest** about trade-offs and uncertainties
- **Include context** that might not be obvious later
- **Tag early** for graduation (#to-adr, #to-skill)
- **Review weekly** to catch patterns

### Don't

- **Over-think** format (templates are guidance, not rules)
- **Wait too long** (context fades quickly)
- **Hide failures** (document what didn't work)
- **Skip the "why"** (most important part)
- **Let journals pile up** (graduate or archive)

---

## Example Entry

See `architecture/2025-12-23-aurora-caching-strategy.md` for a complete example of a well-structured journal entry (to be created during testing).

---

## Related Documentation

- **Commands**: `.claude/commands/README.md` - How slash commands work
- **ADRs**: `docs/adr/README.md` - Formal architecture decisions
- **Skills**: `.claude/skills/README.md` - Formalized expertise
- **CLAUDE.md**: `.claude/CLAUDE.md` - Project principles

---

## Questions?

- How do I create an entry? → Use `/journal category "title"`
- When should I graduate? → When pattern is proven or decision is final
- What if I'm not sure which category? → Start with `meta` - you can recategorize later
- Can I edit entries? → Yes! Journals are living documents until graduated
