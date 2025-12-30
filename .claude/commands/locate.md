---
name: locate
description: Reverse-map from task/feature to implementing files - find where functionality lives in the codebase
accepts_args: true
arg_schema:
  - name: task
    required: true
    description: "Feature, functionality, or task to locate (e.g., 'authentication', 'report generation', 'database connections')"
composition:
  - skill: research
---

# /locate - Task to Files Reverse Mapping

**Status**: Active
**Category**: Discovery
**Phase**: Pre-reading (find files before reading them)
**Pairs with**: `/impact` (inverse operation: file → effects)

---

## Purpose

Find which files implement a specific task or feature. Provides reverse mapping from task/feature (range) to implementing files (domain).

**Use this command when**:
- Starting work on a feature: "Which files do I need to touch?"
- Onboarding: "Where is authentication implemented?"
- Bug investigation: "Where is error handling for timeouts?"
- Refactoring planning: "Which files implement caching?"
- Knowledge transfer: "Show me all files related to Telegram integration"

**Skip this command when**:
- You already know the file location
- Task is too generic (e.g., "code", "files")
- Looking for specific function/class (use IDE search instead)

---

## Mathematical Relationship

**Domain/Range mapping**:
```
/locate: f⁻¹(y) → x    (inverse: task → files, range → domain)
/impact: f(x) → y      (forward: file → effects, domain → range)
```

**Example**:
```bash
# Reverse mapping (task → files)
/locate "authentication"
→ src/auth/login.py, src/middleware/session.py, tests/test_auth.py

# Forward mapping (file → effects)
/impact "refactor src/auth/login.py"
→ Affects: API routes, tests, Telegram integration, docs
```

---

## Usage

```bash
/locate "task or feature description"
```

### Examples

```bash
# Feature discovery
/locate "authentication"
→ Finds: src/auth/, tests/test_auth.py, docs/AUTH.md

# Subsystem exploration
/locate "report generation"
→ Finds: src/workflow/, src/scoring/, tests/test_workflow.py

# Infrastructure
/locate "database connections"
→ Finds: src/services/aurora.py, src/utils/db_pool.py

# API endpoints
/locate "telegram API"
→ Finds: src/api/telegram_routes.py, src/handlers/telegram.py

# Error handling
/locate "timeout handling"
→ Finds: src/utils/retry.py, src/middleware/timeout.py
```

---

## Algorithm

### Phase 1: Keyword Extraction

```python
def extract_keywords(task: str) -> list[str]:
    """
    Extract searchable keywords from task description.

    1. Convert to lowercase
    2. Split on spaces/hyphens
    3. Expand common abbreviations
    4. Add related terms
    5. Remove stopwords
    """
    keywords = [task.lower()]

    # Expansion rules for common abbreviations
    expansions = {
        "auth": ["auth", "authentication", "login", "session", "credential"],
        "db": ["db", "database", "sql", "query", "connection"],
        "api": ["api", "endpoint", "route", "handler"],
        "cache": ["cache", "redis", "dynamodb", "memcache"],
        "report": ["report", "generate", "scoring", "analysis"],
        "telegram": ["telegram", "tg", "bot", "mini_app"],
        "line": ["line", "line_bot", "messaging"],
        "test": ["test", "pytest", "unittest", "mock"],
        "deploy": ["deploy", "deployment", "cicd", "lambda"],
        "error": ["error", "exception", "failure", "retry"],
    }

    for keyword in task.lower().split():
        if keyword in expansions:
            keywords.extend(expansions[keyword])
        else:
            keywords.append(keyword)

    return list(set(keywords))  # Deduplicate
```

**Example**:
```
Task: "authentication"
Keywords: ["auth", "authentication", "login", "session", "credential"]
```

---

### Phase 2: Codebase Search

**Search strategy** (prioritized):

1. **Filename matches** (highest priority)
   ```bash
   # Use Glob tool
   for keyword in keywords:
       glob **/*{keyword}*.py
   ```

2. **Code matches** (medium priority)
   ```bash
   # Use Grep tool for class/function definitions
   for keyword in keywords:
       grep "(class|def).*{keyword}" src/
   ```

3. **Comment matches** (low priority)
   ```bash
   # Use Grep for comments/docstrings
   for keyword in keywords:
       grep "(#|\"\"\".*{keyword})" src/
   ```

**Example**:
```
Task: "authentication"

Filename matches:
- src/auth/login.py
- src/middleware/session.py
- tests/test_auth.py

Code matches:
- src/utils/security.py (def authenticate_user)
- src/api/routes.py (class AuthHandler)

Comment matches:
- src/config.py (# Authentication settings)
```

---

### Phase 3: Relevance Ranking

**Scoring system**:
```python
def rank_by_relevance(search_results: dict) -> list[tuple[str, int, str]]:
    """
    Score files by match quality.

    Scoring:
    - Filename match: 10 points
    - Code match (class/function): 5 points
    - Comment match: 2 points
    - Multiple keyword matches: +3 points each
    - File in src/ (not tests/): +2 points
    """
    scores = {}

    for file in search_results["filename_matches"]:
        scores[file] = scores.get(file, 0) + 10
        if file.startswith("src/"):
            scores[file] += 2

    for file in search_results["code_matches"]:
        scores[file] = scores.get(file, 0) + 5
        if file.startswith("src/"):
            scores[file] += 2

    for file in search_results["comment_matches"]:
        scores[file] = scores.get(file, 0) + 2

    # Sort by score (descending)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [(file, score, infer_role(file)) for file, score in ranked]
```

**Example**:
```
Ranked files:
1. src/auth/login.py (score: 12) - Authentication logic
2. src/middleware/session.py (score: 12) - Middleware/request processing
3. src/utils/security.py (score: 7) - Utility functions
4. tests/test_auth.py (score: 5) - Test suite
5. src/config.py (score: 2) - Configuration
```

---

### Phase 4: Categorization

**Categories**:
```python
categories = {
    "core": [],        # src/ - Core implementation
    "tests": [],       # tests/ - Test suite
    "config": [],      # config/, .env - Configuration
    "docs": []         # docs/, README - Documentation
}
```

**Categorization rules**:
- `src/**/*.py` → Core implementation
- `tests/**/*.py` → Test suite
- `config/**/*.py`, `.env*` → Configuration
- `docs/**/*.md`, `README.md` → Documentation

---

### Phase 5: Entry Point Detection

**Extract main functions/classes**:
```python
def identify_entry_points(core_files: list[str]) -> dict:
    """
    Find main functions/classes to start reading.

    1. Read file content
    2. Parse for class definitions and top-level functions
    3. Filter to most relevant (containing task keywords)
    """
    entry_points = {}

    for filepath in core_files[:5]:  # Top 5 files only
        content = read_file(filepath)

        # Extract class definitions
        classes = re.findall(r'^class (\w+)', content, re.MULTILINE)

        # Extract function definitions (top-level)
        functions = re.findall(r'^def (\w+)', content, re.MULTILINE)

        entry_points[filepath] = {
            "classes": classes,
            "functions": functions
        }

    return entry_points
```

**Example**:
```
Entry points:
- src/auth/login.py
  - Classes: AuthHandler
  - Functions: authenticate_user, validate_credentials

- src/middleware/session.py
  - Classes: SessionMiddleware
  - Functions: validate_token, refresh_session
```

---

## Output

### Chat Summary

```
✅ Located files implementing "authentication"

Files found: 8 total
- Core implementation: 3 files
- Tests: 2 files
- Configuration: 2 files
- Documentation: 1 file

Top files:
1. src/auth/login.py - Authentication logic
2. src/middleware/session.py - Middleware/request processing
3. src/utils/security.py - Utility functions

Entry points:
- src/auth/login.py:authenticate_user()
- src/middleware/session.py:validate_token()

Full report: .claude/locate/2025-12-28-authentication.md

Next steps:
  read src/auth/login.py
  read src/middleware/session.py
```

---

### Full Report (saved to `.claude/locate/{date}-{task-slug}.md`)

```markdown
# Locate: Authentication Implementation

**Date**: 2025-12-28
**Task**: "authentication"
**Keywords**: ["auth", "authentication", "login", "session", "credential"]
**Status**: Complete

---

## Files Found (8 total)

### Core Implementation (3 files)

1. `src/auth/login.py` - Authentication logic
   - Classes: `AuthHandler`
   - Functions: `authenticate_user()`, `validate_credentials()`
   - Score: 12 (filename match + src/ bonus)

2. `src/middleware/session.py` - Middleware/request processing
   - Classes: `SessionMiddleware`
   - Functions: `validate_token()`, `refresh_session()`
   - Score: 12

3. `src/utils/security.py` - Utility functions
   - Functions: `hash_password()`, `generate_jwt()`
   - Score: 7 (code match + src/ bonus)

### Tests (2 files)

4. `tests/test_auth.py` - Auth integration tests
   - Score: 5

5. `tests/test_security.py` - Security utility unit tests
   - Score: 5

### Configuration (2 files)

6. `config/auth_config.py` - Auth settings (JWT secret, expiry)
   - Score: 2

7. `.env.example` - Environment variables for auth
   - Score: 2

### Documentation (1 file)

8. `docs/AUTH.md` - Authentication flow documentation
   - Score: 2

---

## Entry Points

**Start here**:
- Login flow: `src/auth/login.py:authenticate_user()`
- Session validation: `src/middleware/session.py:validate_token()`

**Read order** (suggested):
1. `src/auth/login.py` - Understand login flow
2. `src/middleware/session.py` - Understand session management
3. `src/utils/security.py` - Understand security utilities

---

## Related Tasks

```bash
# Explore related features
/locate "password reset"
/locate "user registration"
/locate "OAuth integration"

# Assess impact before changing
/impact "refactor src/auth/login.py to use OAuth2"
```

---

## Next Steps

```bash
# Read core implementation
read src/auth/login.py
read src/middleware/session.py

# Check test coverage
pytest tests/test_auth.py -v

# Review configuration
read config/auth_config.py
```

---

*Generated by `/locate` command*
*Duration: 3.2 seconds*
```

---

## Integration with Other Commands

### Sequential Workflow (Recommended)

```bash
# Step 1: Locate files for task
/locate "authentication"
→ Output: src/auth/login.py, src/middleware/session.py

# Step 2: Read files to understand implementation
read src/auth/login.py
read src/middleware/session.py

# Step 3: Assess impact before making changes
/impact "refactor src/auth/login.py to use OAuth2"
→ Output: Affects API routes, tests, Telegram integration

# Step 4: Plan refactoring
EnterPlanMode
```

---

### Complementary Commands

**`/locate` vs `/explore`**:

| Aspect | `/locate` | `/explore` |
|--------|-----------|------------|
| **Purpose** | Find files | Explore solutions |
| **Input** | Task/feature | Problem statement |
| **Output** | File list | Research document |
| **Use case** | "Where is X?" | "How should I implement X?" |

**Example**:
```bash
# Use /locate to FIND existing implementation
/locate "database connections"
→ src/services/aurora.py, src/utils/db_pool.py

# Use /explore to UNDERSTAND approach or alternatives
/explore "How do we currently handle database connections"
→ Research doc analyzing connection pooling pattern
```

---

**`/locate` vs `/impact`**:

| Aspect | `/locate` | `/impact` |
|--------|-----------|-----------|
| **Direction** | Range → Domain | Domain → Range |
| **Input** | Feature/task | File/change |
| **Output** | Files implementing | Components affected |
| **Timing** | Before reading | Before changing |

**Example**:
```bash
# Locate files (task → files)
/locate "authentication"
→ src/auth/login.py, src/middleware/session.py

# Impact analysis (file → effects)
/impact "refactor src/auth/login.py"
→ Affects: tests/, docs/, API routes
```

---

## Error Handling

**Common errors and solutions**:

### Error: No Matches Found

```
❌ No files found matching "authentication"

Suggestions:
- Try broader keywords: /locate "auth"
- Check spelling
- Try related terms: /locate "login" or /locate "session"
```

**Solution**: Use broader or alternative keywords

---

### Error: Too Many Matches

```
⚠️ Found 150 matches for "test"

Results truncated to top 50 files.

Suggestions:
- Be more specific: /locate "integration test"
- Add context: /locate "authentication test"
```

**Solution**: Refine task description with more specific keywords

---

### Error: Empty Task

```
❌ Task description required

Usage: /locate "feature name"

Examples:
  /locate "authentication"
  /locate "report generation"
  /locate "database connections"
```

**Solution**: Provide task description

---

## Performance

**Expected duration**:
- Best case: 1-2 seconds (small codebase, clear matches)
- Average case: 3-5 seconds (medium codebase, keyword expansion)
- Worst case: 8-10 seconds (large codebase, many matches)

**Bottlenecks**:
- Grep operations (keyword search across codebase)
- File reading for entry point detection

**Optimization**:
- Results limited to top 50 files
- Entry points detected for top 5 core files only
- Parallel keyword searches where possible

---

## Anti-Patterns

### ❌ Don't Use /locate For

**Too generic** (results will be overwhelming):
```bash
# Bad
/locate "code"
/locate "files"
/locate "function"

# Good - be specific
/locate "authentication code"
/locate "configuration files"
/locate "report generation functions"
```

---

**Already know location** (waste of time):
```bash
# Bad - if you already know the file
/locate "login.py"

# Good - just read it
read src/auth/login.py
```

---

**Looking for specific function** (use IDE/grep directly):
```bash
# Bad - too specific for /locate
/locate "authenticate_user function"

# Good - use grep directly or LSP
grep "def authenticate_user" src/
# or use IDE "Go to Definition"
```

---

**Extremely specific queries** (likely zero results):
```bash
# Bad - too narrow
/locate "the function that validates JWT tokens on line 42"

# Good - broader task
/locate "JWT validation"
```

---

## Examples

### Example 1: Feature Discovery

**Scenario**: New developer wants to understand authentication

```bash
/locate "authentication"
```

**Output**:
```
✅ Located files implementing "authentication"

Files found: 8 total
- Core: src/auth/login.py, src/middleware/session.py, src/utils/security.py
- Tests: tests/test_auth.py, tests/test_security.py
- Config: config/auth_config.py, .env.example
- Docs: docs/AUTH.md

Entry points:
- src/auth/login.py:authenticate_user()
- src/middleware/session.py:validate_token()

Next: read src/auth/login.py
```

---

### Example 2: Bug Investigation

**Scenario**: Investigating timeout errors

```bash
/locate "timeout handling"
```

**Output**:
```
✅ Located files implementing "timeout handling"

Files found: 5 total
- Core: src/utils/retry.py, src/middleware/timeout.py
- Tests: tests/test_retry.py

Entry points:
- src/utils/retry.py:retry_with_timeout()
- src/middleware/timeout.py:TimeoutMiddleware

Next: read src/utils/retry.py
```

---

### Example 3: Refactoring Planning

**Scenario**: Planning to refactor caching strategy

```bash
# Step 1: Locate all caching code
/locate "cache"
```

**Output**:
```
✅ Located files implementing "cache"

Files found: 7 files
- Core: src/cache/redis.py, src/cache/dynamodb.py
- Tests: tests/test_cache.py

Entry points:
- src/cache/redis.py:RedisCache
- src/cache/dynamodb.py:DynamoDBCache
```

```bash
# Step 2: Read implementations
read src/cache/redis.py
read src/cache/dynamodb.py

# Step 3: Assess impact of changes
/impact "consolidate caching into single DynamoDB implementation"
```

---

## Best Practices

### ✅ Do

**Be specific enough**:
```bash
/locate "authentication"        # Good - clear feature
/locate "JWT token validation"  # Good - specific task
/locate "Telegram API"          # Good - subsystem
```

**Use task-oriented language**:
```bash
/locate "error handling"        # Good - what it does
/locate "report generation"     # Good - what it does
/locate "database connections"  # Good - what it does
```

**Follow up with impact analysis**:
```bash
/locate "authentication"
read src/auth/login.py
/impact "refactor authentication to use OAuth2"
```

---

### ❌ Don't

**Be too generic**:
```bash
/locate "code"      # Bad - too broad
/locate "API"       # Bad - too broad
```

**Use file names**:
```bash
/locate "login.py"  # Bad - just use: read src/auth/login.py
```

**Chain multiple tasks**:
```bash
/locate "authentication and authorization and session management"
# Bad - too complex, split into separate queries

# Good - separate queries
/locate "authentication"
/locate "authorization"
/locate "session management"
```

---

## Success Criteria

Command is successful when:

- [x] Finds relevant files (>80% precision)
- [x] Ranks files by relevance correctly
- [x] Categorizes files appropriately
- [x] Identifies entry points for core files
- [x] Completes in <10 seconds
- [x] Provides actionable next steps
- [x] Handles errors gracefully

---

## Future Enhancements

**Phase 2** (after validation):
- Add `--lang` filter: `/locate "auth" --lang=python`
- Add `--exclude` filter: `/locate "auth" --exclude=tests`
- Analyze import relationships (dependency graph)
- Cache results for common tasks

**Phase 3** (if successful):
- Add to CLAUDE.md as "Reverse Discovery Principle"
- Create abstraction for task→files pattern
- Extend to other domains (`/locate-config`, `/locate-docs`)

---

## Related Commands

- `/impact` - Assess change impact (inverse of /locate)
- `/explore` - Explore solution alternatives
- `/refactor` - Identify files needing refactoring
- `/bug-hunt` - Investigate errors (uses task→files for error symptoms)

---

## See Also

- `.claude/commands/impact.md` - Forward mapping (file → effects)
- `.claude/commands/explore.md` - Solution exploration
- `.claude/evolution/2025-12-28-locate-command-proposal.md` - Evolution analysis
- `.claude/specifications/workflow/2025-12-28-implement-locate-command.md` - Implementation spec

---

**Owner**: Platform team
**Created**: 2025-12-28
**Status**: Active
