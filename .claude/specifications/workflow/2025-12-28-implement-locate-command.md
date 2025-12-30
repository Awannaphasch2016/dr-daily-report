---
title: Implement /locate Command
focus: workflow
date: 2025-12-28
status: draft
tags: [cli, metacognition, file-discovery, reverse-mapping]
---

# Workflow Specification: Implement /locate Command

## Goal

**What does this workflow accomplish?**

Implement the `/locate` command that performs reverse mapping from tasks/features to implementing files. This fills the identified gap in the command system where `/impact` provides forward mapping (file → effects) but no command provides inverse mapping (task → files).

**Input**: Task/feature description (e.g., "authentication", "report generation")
**Output**: Categorized list of files implementing that task with entry points and relevance ranking

---

## Workflow Diagram

```
[User invokes] → [Parse args] → [Extract keywords] → [Search codebase]
                                                            ↓
[Output report] ← [Categorize files] ← [Rank by relevance] ←
```

---

## Implementation Nodes

### Node 1: Create Command Specification

**Purpose**: Define command YAML frontmatter and documentation

**File**: `.claude/commands/locate.md`

**Processing**:
1. Create YAML frontmatter with command metadata
2. Write command documentation (purpose, usage, examples)
3. Define algorithm specification
4. Document integration with other commands

**Output**: Command specification file

**Duration**: ~5 minutes (documentation writing)

**Error conditions**:
- File already exists: Overwrite with warning
- Invalid YAML syntax: Validation error

---

### Node 2: Extract Keywords from Task Description

**Purpose**: Convert user's task description into searchable keywords

**Input**:
```python
task = "authentication"  # User-provided task
```

**Processing**:
```python
def extract_keywords(task: str) -> list[str]:
    """
    Extract searchable keywords from task description.

    Algorithm:
    1. Convert to lowercase
    2. Split on spaces/hyphens
    3. Expand common abbreviations (auth → authentication)
    4. Add related terms (login, session for authentication)
    5. Remove stopwords (the, a, an, is, etc.)
    """
    keywords = [task.lower()]

    # Expansion rules
    expansions = {
        "auth": ["auth", "authentication", "login", "session", "credential"],
        "db": ["db", "database", "sql", "query", "connection"],
        "api": ["api", "endpoint", "route", "handler"],
        "cache": ["cache", "redis", "dynamodb", "memcache"],
        "report": ["report", "generate", "scoring", "analysis"],
        # ... more expansions
    }

    for keyword in task.lower().split():
        if keyword in expansions:
            keywords.extend(expansions[keyword])
        else:
            keywords.append(keyword)

    return list(set(keywords))  # Deduplicate
```

**Output**:
```python
["auth", "authentication", "login", "session", "credential"]
```

**Duration**: <1 second

**Error conditions**:
- Empty task: Return error "Task description required"
- Too generic (e.g., "code"): Warn "Task too generic, results may be broad"

---

### Node 3: Search Codebase with Keywords

**Purpose**: Find all files matching keywords using Glob and Grep

**Input**:
```python
keywords = ["auth", "authentication", "login", "session"]
```

**Processing**:
```python
def search_codebase(keywords: list[str]) -> dict[str, list[str]]:
    """
    Search codebase for files matching keywords.

    Strategy:
    1. Filename matches (highest priority)
    2. Class/function name matches (medium priority)
    3. Comment/docstring matches (low priority)
    """
    results = {
        "filename_matches": [],
        "code_matches": [],
        "comment_matches": []
    }

    # Search 1: Filename matches
    for keyword in keywords:
        # Use Glob tool
        glob_pattern = f"**/*{keyword}*.py"
        filename_matches = glob(glob_pattern, ["src/", "tests/"])
        results["filename_matches"].extend(filename_matches)

    # Search 2: Code matches (class/function definitions)
    for keyword in keywords:
        # Use Grep tool for class/function definitions
        grep_pattern = f"(class|def).*{keyword}"
        code_matches = grep(grep_pattern, path="src/", output_mode="files_with_matches")
        results["code_matches"].extend(code_matches)

    # Search 3: Comment matches
    for keyword in keywords:
        # Use Grep for comments/docstrings
        grep_pattern = f"(#|\"\"\".*{keyword})"
        comment_matches = grep(grep_pattern, path="src/", output_mode="files_with_matches")
        results["comment_matches"].extend(comment_matches)

    return results
```

**Output**:
```python
{
    "filename_matches": [
        "src/auth/login.py",
        "src/middleware/session.py"
    ],
    "code_matches": [
        "src/utils/security.py",  # def authenticate_user()
        "src/api/routes.py"        # class AuthHandler
    ],
    "comment_matches": [
        "src/config.py"  # Comment: "Authentication settings"
    ]
}
```

**Duration**: 1-3 seconds (depending on codebase size)

**Error conditions**:
- No matches found: Return empty results with suggestion to try broader keywords
- Too many matches (>100): Warn "Too many matches, refine task description"

---

### Node 4: Rank Files by Relevance

**Purpose**: Score files by match quality and relevance

**Input**:
```python
{
    "filename_matches": ["src/auth/login.py", "src/middleware/session.py"],
    "code_matches": ["src/utils/security.py", "src/api/routes.py"],
    "comment_matches": ["src/config.py"]
}
```

**Processing**:
```python
def rank_by_relevance(search_results: dict) -> list[tuple[str, int, str]]:
    """
    Score files by relevance.

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

    # Infer role from file path
    def infer_role(filepath: str) -> str:
        if "auth" in filepath or "login" in filepath:
            return "Authentication logic"
        elif "middleware" in filepath:
            return "Middleware/request processing"
        elif "api" in filepath or "routes" in filepath:
            return "API endpoints"
        elif "utils" in filepath:
            return "Utility functions"
        elif "config" in filepath:
            return "Configuration"
        elif "tests" in filepath:
            return "Test suite"
        else:
            return "Implementation"

    return [(file, score, infer_role(file)) for file, score in ranked]
```

**Output**:
```python
[
    ("src/auth/login.py", 12, "Authentication logic"),
    ("src/middleware/session.py", 12, "Middleware/request processing"),
    ("src/utils/security.py", 7, "Utility functions"),
    ("src/api/routes.py", 7, "API endpoints"),
    ("src/config.py", 2, "Configuration")
]
```

**Duration**: <1 second

---

### Node 5: Categorize Files

**Purpose**: Group files by role (core, tests, config, docs)

**Input**:
```python
[
    ("src/auth/login.py", 12, "Authentication logic"),
    ("src/middleware/session.py", 12, "Middleware/request processing"),
    ("tests/test_auth.py", 5, "Test suite"),
    ("config/auth_config.py", 2, "Configuration"),
    ("docs/AUTH.md", 2, "Documentation")
]
```

**Processing**:
```python
def categorize_files(ranked_files: list[tuple]) -> dict:
    """
    Categorize files by role.

    Categories:
    - Core implementation (src/)
    - Tests (tests/)
    - Configuration (config/, .env)
    - Documentation (docs/, README)
    """
    categories = {
        "core": [],
        "tests": [],
        "config": [],
        "docs": []
    }

    for filepath, score, role in ranked_files:
        if filepath.startswith("src/"):
            categories["core"].append((filepath, role))
        elif filepath.startswith("tests/"):
            categories["tests"].append((filepath, role))
        elif filepath.startswith("config/") or ".env" in filepath:
            categories["config"].append((filepath, role))
        elif filepath.startswith("docs/") or "README" in filepath:
            categories["docs"].append((filepath, role))

    return categories
```

**Output**:
```python
{
    "core": [
        ("src/auth/login.py", "Authentication logic"),
        ("src/middleware/session.py", "Middleware/request processing")
    ],
    "tests": [
        ("tests/test_auth.py", "Test suite")
    ],
    "config": [
        ("config/auth_config.py", "Configuration")
    ],
    "docs": [
        ("docs/AUTH.md", "Documentation")
    ]
}
```

**Duration**: <1 second

---

### Node 6: Identify Entry Points

**Purpose**: Find main functions/classes to start reading

**Input**:
```python
core_files = [
    "src/auth/login.py",
    "src/middleware/session.py"
]
```

**Processing**:
```python
def identify_entry_points(core_files: list[str]) -> dict[str, list[str]]:
    """
    Read each core file and extract main functions/classes.

    Algorithm:
    1. Read file content
    2. Parse for class definitions and top-level functions
    3. Filter to most relevant (containing task keywords)
    """
    entry_points = {}

    for filepath in core_files:
        content = read_file(filepath)

        # Extract class definitions
        classes = re.findall(r'^class (\w+)', content, re.MULTILINE)

        # Extract function definitions (top-level only, not nested)
        functions = re.findall(r'^def (\w+)', content, re.MULTILINE)

        entry_points[filepath] = {
            "classes": classes,
            "functions": functions
        }

    return entry_points
```

**Output**:
```python
{
    "src/auth/login.py": {
        "classes": ["AuthHandler"],
        "functions": ["authenticate_user", "validate_credentials"]
    },
    "src/middleware/session.py": {
        "classes": ["SessionMiddleware"],
        "functions": ["validate_token", "refresh_session"]
    }
}
```

**Duration**: 1-2 seconds

**Error conditions**:
- File not readable: Skip with warning
- Parse error: Continue with empty entry points

---

### Node 7: Generate Output Report

**Purpose**: Format results as markdown report

**Input**:
```python
task = "authentication"
categorized_files = {...}
entry_points = {...}
```

**Processing**:
```python
def generate_report(task: str, categories: dict, entry_points: dict) -> str:
    """
    Generate markdown report.

    Format:
    - Header with task and metadata
    - Files found by category
    - Entry points for core files
    - Suggested next steps
    """
    report = f"""# Locate: {task.title()} Implementation

**Date**: {datetime.now().strftime('%Y-%m-%d')}
**Task**: "{task}"
**Status**: Complete

---

## Files Found ({total_count} total)

### Core Implementation ({len(categories['core'])} files)
"""

    for i, (filepath, role) in enumerate(categories["core"], 1):
        report += f"{i}. `{filepath}` - {role}\n"

        # Add entry points if available
        if filepath in entry_points:
            ep = entry_points[filepath]
            if ep["classes"]:
                report += f"   - Classes: {', '.join(ep['classes'])}\n"
            if ep["functions"]:
                report += f"   - Functions: {', '.join(ep['functions'])}\n"

    # Add other categories...
    report += "\n### Tests (...)\n"
    report += "\n### Configuration (...)\n"
    report += "\n### Documentation (...)\n"

    report += """
---

## Entry Points

**Start here**:
"""

    # Suggest first file to read
    if categories["core"]:
        first_file = categories["core"][0][0]
        report += f"- Read: `{first_file}`\n"

        if first_file in entry_points:
            ep = entry_points[first_file]
            if ep["functions"]:
                report += f"  - Entry function: `{ep['functions'][0]}()`\n"

    report += """
---

## Next Steps

```bash
# Read core implementation
"""

    for filepath, _ in categories["core"][:3]:  # Top 3 files
        report += f"read {filepath}\n"

    report += """
# Check test coverage
pytest {test_files} -v

# Review related features
/locate "related feature"
```
"""

    return report
```

**Output**: Markdown report (saved to `.claude/locate/{date}-{task-slug}.md`)

**Duration**: <1 second

---

### Node 8: Display Summary to User

**Purpose**: Show concise summary in chat

**Input**: Full report

**Processing**: Extract key metrics and top files

**Output**:
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

**Duration**: Immediate

---

## State Management

**State structure**:
```python
class LocateState(TypedDict):
    task: str                          # User-provided task
    keywords: list[str]                # Extracted keywords
    search_results: dict[str, list]    # Raw search results
    ranked_files: list[tuple]          # Scored files
    categorized_files: dict            # Files by category
    entry_points: dict                 # Main functions/classes
    report: str                        # Final markdown report
    error: Optional[str]               # Error message if any
```

**State transitions**:
- Initial → After keyword extraction: `state["keywords"]` populated
- After search → After ranking: `state["search_results"]` → `state["ranked_files"]`
- After categorization → After entry point detection: `state["categorized_files"]` → `state["entry_points"]`
- After report generation: `state["report"]` populated

---

## Error Handling

**Error propagation**:
- Nodes set `state["error"]` on failure
- Workflow continues with degraded results (e.g., no entry points found, but files still listed)

**Retry logic**:
- Transient errors (file read failures): Skip file, continue
- Permanent errors (no matches found): Return empty results with helpful message

**User-facing errors**:
```python
errors = {
    "EMPTY_TASK": "Task description required. Usage: /locate \"feature name\"",
    "NO_MATCHES": "No files found matching '{task}'. Try broader keywords.",
    "TOO_MANY_MATCHES": "Found {count} matches. Refine task description for better results.",
    "SEARCH_FAILED": "Codebase search failed. Check file permissions."
}
```

---

## Performance

**Expected duration**:
- Best case: 1-2 seconds (small codebase, clear matches)
- Average case: 3-5 seconds (medium codebase, keyword expansion)
- Worst case: 8-10 seconds (large codebase, many matches requiring ranking)

**Bottlenecks**:
- Grep operations (most time-consuming)
- File reading for entry point detection

**Optimization opportunities**:
- Cache search results for common tasks
- Parallelize Grep operations (multiple keywords simultaneously)
- Limit entry point detection to top 5 files only

---

## Integration with Existing Commands

**Complementary commands**:

```bash
# Workflow: Locate → Read → Impact
/locate "authentication"
  → Output: src/auth/login.py, src/middleware/session.py

read src/auth/login.py
  → Understand implementation

/impact "refactor src/auth/login.py"
  → Assess downstream effects before changing
```

**Domain/Range relationship**:
```
/locate: f⁻¹(y) → x    (task → files, range → domain)
/impact: f(x) → y      (file → effects, domain → range)
```

---

## Testing Strategy

**Unit tests**:
```python
def test_extract_keywords():
    assert "auth" in extract_keywords("authentication")
    assert "login" in extract_keywords("authentication")

def test_rank_by_relevance():
    results = {
        "filename_matches": ["src/auth.py"],
        "code_matches": ["src/utils.py"],
        "comment_matches": ["src/config.py"]
    }
    ranked = rank_by_relevance(results)
    assert ranked[0][0] == "src/auth.py"  # Filename match ranks highest

def test_categorize_files():
    files = [
        ("src/auth.py", 10, "Core"),
        ("tests/test_auth.py", 5, "Tests")
    ]
    categories = categorize_files(files)
    assert len(categories["core"]) == 1
    assert len(categories["tests"]) == 1
```

**Integration tests**:
```bash
# Test against actual codebase
/locate "authentication"
  → Verify finds src/auth/, tests/test_auth.py

/locate "report generation"
  → Verify finds src/workflow/, src/scoring/

/locate "nonexistent feature"
  → Verify returns "No matches found" error
```

---

## Open Questions

- [x] Should we cache search results? → NO (codebase changes frequently)
- [x] How many files to show in summary? → Top 10, full list in report
- [ ] Should we analyze import relationships? → Future enhancement
- [ ] Support filtering by file type (--lang=python)? → Future enhancement

---

## Next Steps

### Implementation Sequence

1. **Create command specification** (`.claude/commands/locate.md`)
   - Define YAML frontmatter
   - Write documentation
   - Document algorithm

2. **Implement keyword extraction**
   - Write `extract_keywords()` function
   - Add expansion rules for common abbreviations
   - Test with sample inputs

3. **Implement codebase search**
   - Use Glob for filename matches
   - Use Grep for code/comment matches
   - Aggregate results

4. **Implement ranking and categorization**
   - Score files by match quality
   - Group by role (core/tests/config/docs)
   - Sort by relevance

5. **Implement entry point detection**
   - Read core files
   - Extract class/function definitions
   - Match against keywords

6. **Implement report generation**
   - Format as markdown
   - Save to `.claude/locate/`
   - Display summary to user

7. **Test with real examples**
   - `/locate "authentication"`
   - `/locate "report generation"`
   - `/locate "database connections"`

8. **Document in PROJECT_CONVENTIONS.md**
   - Add to CLI command list
   - Add usage examples
   - Document integration with `/impact`

9. **Journal first usage**
   - Document friction reduced vs manual grep
   - Note any issues or improvements needed

---

## Success Criteria

- [x] Command specification complete
- [ ] Keyword extraction working correctly
- [ ] Search finds relevant files (>80% precision)
- [ ] Ranking prioritizes most relevant files
- [ ] Entry points correctly identified
- [ ] Report format is readable and actionable
- [ ] Performance acceptable (<10 seconds)
- [ ] Error handling covers common cases
- [ ] Integration with `/impact` documented
- [ ] Usage documented in PROJECT_CONVENTIONS.md

---

## Future Enhancements

**Phase 2** (after validation):
- Add `--lang` filter (e.g., `/locate "auth" --lang=python`)
- Add `--exclude` filter (e.g., `/locate "auth" --exclude=tests`)
- Analyze import relationships (show dependency graph)
- Cache results for common tasks
- Add relevance scoring based on git history (recently modified files rank higher)

**Phase 3** (if successful):
- Graduate to CLAUDE.md as "Reverse Discovery Principle"
- Create abstraction for task→files pattern
- Extend to other domains (e.g., `/locate-config`, `/locate-docs`)

---

*Specification created: 2025-12-28*
*Status: Ready for implementation*
