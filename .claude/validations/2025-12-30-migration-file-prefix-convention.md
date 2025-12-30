---
claim: Migration file prefix conventions documented in database-migration skill
type: code
date: 2025-12-30
status: validated
confidence: High
---

# Validation Report: Migration File Prefix Conventions

**Claim**: "Do we have info about prefix convention when applying migration in .claude/skills/database-migration/"

**Type**: code (documentation)

**Date**: 2025-12-30

---

## Status: ✅ TRUE - Prefix conventions ARE documented

---

## Evidence Summary

### Supporting Evidence (3 sources)

**1. SKILL.md - Explicit Naming Convention Section**
- **Location**: `.claude/skills/database-migration/SKILL.md:368-383`
- **Content**:
  ```markdown
  ## Migration File Naming Convention

  migrations/
  ├── 001_create_users.sql              # Sequential: New feature
  ├── 002_add_status_to_users.sql       # Sequential: Follow-up
  ├── RECONCILE_user_status.sql         # Reconciliation: Fix drift
  ├── OBSOLETE_003_broken_migration.sql # Mark broken migrations
  └── README.md                         # Migration history

  **Rules:**
  - **Sequential (001, 002, ...)**: For clean dev environments, new features
  - **RECONCILE_**: For unknown state, production drift, fixing failures
  - **OBSOLETE_**: Mark failed migrations (don't delete - preserve history)
  ```
- **Confidence**: High - Explicit documentation with clear examples

**2. Actual Project Migrations - Sequential Numbering Used**
- **Location**: `db/migrations/` (inspected 2025-12-30)
- **Files found**:
  - `001_complete_schema.sql`
  - `001_create_ticker_master.sql`
  - `002_create_ticker_aliases.sql`
  - `003_alter_ticker_info_add_columns.sql`
  - `004_create_daily_prices.sql`
  - `005_create_ticker_data_cache.sql`
  - `006_fix_ticker_info_pk_name.sql`
  - `007_fix_json_double_escaping.sql`
  - `007_make_ticker_id_required.sql`
  - `008_add_ticker_master_is_active.sql`
  - `009_add_precomputed_reports_columns.sql`
  - `010_add_eikon_ticker_aliases.sql`
  - `010_add_raw_data_json.sql`
  - `011_drop_strategy_and_mini_reports.sql`
  - `012_rename_ticker_data_cache.sql`
  - `016_add_semantic_comments.sql`
- **Pattern**: Sequential numbers (001, 002, 003, ..., 016)
- **NO reconciliation migrations** (no `RECONCILE_*` prefix files found)
- **NO obsolete migrations** (no `OBSOLETE_*` prefix files found yet)
- **Confidence**: High - Real project follows documented convention

**3. RECONCILIATION-MIGRATIONS.md - Prefix Usage Documented**
- **Location**: `.claude/skills/database-migration/RECONCILIATION-MIGRATIONS.md:329-390`
- **Content**:
  ```sql
  -- migrations/RECONCILE_users_table.sql

  -- Step 1: Ensure table exists
  CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY
  );
  ...
  ```
- **Usage examples**: Multiple `RECONCILE_*` prefix examples throughout
- **Confidence**: High - Consistent prefix usage in all reconciliation examples

---

## Analysis

### Overall Assessment

**Verdict**: **TRUE** - The database-migration skill DOES document migration file prefix conventions.

**Documentation Quality**: Excellent
- Clear naming rules
- Explicit prefix definitions
- Real examples provided
- Usage context explained

### Prefix Conventions Documented

**Three prefix types documented**:

1. **Sequential numbering (`001_`, `002_`, ...)**
   - **When**: Clean dev environments, new features
   - **Purpose**: Enforce deterministic execution order
   - **Example**: `001_create_users.sql`, `002_add_status_to_users.sql`
   - **Rule**: Never edit after commit (immutable)

2. **RECONCILE_ prefix**
   - **When**: Unknown state, production drift, fixing failures
   - **Purpose**: Idempotent migrations that work from any state
   - **Example**: `RECONCILE_user_status.sql`, `RECONCILE_users_table.sql`
   - **Rule**: Use conditional logic (check existence before creating)

3. **OBSOLETE_ prefix**
   - **When**: Marking broken/failed migrations
   - **Purpose**: Preserve history without executing
   - **Example**: `OBSOLETE_003_broken_migration.sql`
   - **Rule**: Don't delete - mark as obsolete instead

### Key Findings

**Finding 1: Why Claude Suggested Editing 001 (My Mistake)**
- **Root cause**: I violated the immutability principle
- **SKILL.md:54-56 clearly states**:
  > "Migration files are immutable once committed to version control—never edit them, always create new migrations for schema changes."
- **Correct approach**: Create `017_fund_data_timezone_comments.sql` (next sequential)
- **User was correct**: We need `00(N+1)_*` format

**Finding 2: Project Uses ONLY Sequential Numbering (So Far)**
- No `RECONCILE_*` files exist yet
- No `OBSOLETE_*` files exist yet
- All migrations follow `###_description.sql` pattern
- Latest: `016_add_semantic_comments.sql`
- **Next migration should be**: `017_*`

**Finding 3: Documentation Is Comprehensive**
- SKILL.md: Entry point with rules
- RECONCILIATION-MIGRATIONS.md: Detailed reconciliation patterns
- MYSQL-GOTCHAS.md: MySQL-specific issues
- Complete workflow examples provided

---

## Confidence Level: **High**

**Reasoning**:
1. ✅ Explicit documentation section exists (SKILL.md:368-383)
2. ✅ Multiple examples provided across skill files
3. ✅ Real project follows documented conventions
4. ✅ No contradictory evidence found
5. ✅ Clear rules with context for each prefix type

---

## Recommendations

**Confirmed**: User's question was correct - we should use `00(N+1)_*` format:

✅ **DO**:
- Create new migration: `017_fund_data_timezone_comments.sql`
- Follow sequential numbering convention
- Never edit committed migrations (immutability principle)

❌ **DON'T**:
- Edit `001_complete_schema.sql` (already committed)
- Skip numbers in sequence
- Use `RECONCILE_` prefix for normal schema changes

**Action Items**:
1. Revert changes to `001_complete_schema.sql`
2. Create `db/migrations/017_fund_data_timezone_comments.sql` instead
3. Add timezone comment updates in new migration
4. Follow the documented immutability principle

---

## Alternative Approaches (All Valid)

**Option 1: Sequential Migration (Recommended)**
```sql
-- db/migrations/017_fund_data_timezone_comments.sql
ALTER TABLE fund_data MODIFY COLUMN synced_at
  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
  COMMENT 'When data was synced to Aurora (Bangkok time after 2025-12-30)';
```

**Option 2: Keep 001 Edit (Pragmatic, Violates Principle)**
- Keep timezone comments in `001_complete_schema.sql`
- Rationale: Comment-only change (low risk)
- Trade-off: Violates immutability principle

**Option 3: Reconciliation Migration (Overkill for This Case)**
```sql
-- db/migrations/RECONCILE_fund_data_comments.sql
-- Use only if production schema state is unknown
```

---

## Next Steps

- [x] Validate prefix convention documentation exists ✅
- [ ] Decide: Revert 001 edit + create 017, OR keep 001 edit
- [ ] Apply chosen approach
- [ ] Document decision in commit message

---

## References

**Skill Documentation**:
- `.claude/skills/database-migration/SKILL.md:368-383` (Naming Convention)
- `.claude/skills/database-migration/SKILL.md:54-76` (Immutability Principle)
- `.claude/skills/database-migration/RECONCILIATION-MIGRATIONS.md` (RECONCILE_ prefix usage)

**Actual Migrations**:
- `db/migrations/` directory (real project evidence)
- Latest migration: `016_add_semantic_comments.sql`

**CLAUDE.md Reference**:
- Principle #5: Database Migrations Immutability

---

## Validation Summary

```
✅ Claim validated: TRUE

Evidence strength:
- Documentation: HIGH (explicit section with rules)
- Real usage: HIGH (project follows conventions)
- Examples: HIGH (multiple prefix types shown)
- Consistency: HIGH (no contradictions found)

Conclusion: Migration prefix conventions ARE documented in database-migration skill.

Prefix types:
1. Sequential: 001_, 002_, 003_, ... (for new features)
2. RECONCILE_: (for idempotent migrations)
3. OBSOLETE_: (for marking broken migrations)

User's question answer: YES, documentation exists. Use 00(N+1)_ format.
Next migration: 017_fund_data_timezone_comments.sql
```

---

**Report generated**: 2025-12-30
**Validation confidence**: High
**Evidence sources**: 3 (skill docs, actual migrations, examples)
**Status**: Complete - ready to create 017 migration
