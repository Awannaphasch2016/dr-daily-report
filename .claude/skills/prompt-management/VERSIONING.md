# Prompt Versioning

**Reference**: Managing prompt versions across environments.

---

## Versioning Model

Langfuse uses two complementary systems:

### 1. Numeric Versions (Immutable)

```
dr-report-main v1 → v2 → v3 → v4
                         ↑
                    Each version immutable
```

- Auto-incremented on save
- Immutable once created
- Used for rollback and audit

### 2. Labels (Mutable Pointers)

```
production → v3
staging    → v4
dev        → v5
```

- Mutable pointers to versions
- Multiple labels per version OK
- Used for environment routing

---

## Environment Promotion Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Prompt: dr-report-main               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  v5 ←── dev                                             │
│  v4 ←── staging                                         │
│  v3 ←── production                                      │
│  v2                                                     │
│  v1                                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘

Promotion: Move label to newer version
Rollback:  Move label to older version
```

### Promotion Steps

1. **Create new version** in Langfuse UI or API
2. **Test in dev**: Set `dev` label to new version
3. **Validate in staging**: Set `staging` label after dev passes
4. **Deploy to production**: Set `production` label after staging passes

---

## Label Strategy

### Recommended Labels

| Label | Purpose | Traffic |
|-------|---------|---------|
| `production` | Live user traffic | 100% (default) |
| `staging` | Pre-production testing | Manual testing |
| `dev` | Development testing | Local only |
| `prod-a` | A/B test variant A | 50% (A/B) |
| `prod-b` | A/B test variant B | 50% (A/B) |

### Fetching by Label

```python
# Production (default)
prompt = langfuse.get_prompt("dr-report-main", label="production")

# Environment-specific
env = os.getenv("ENVIRONMENT", "dev")
prompt = langfuse.get_prompt("dr-report-main", label=env)
```

---

## Version Management in Code

### Current Implementation

```python
# src/integrations/prompt_service.py
class PromptService:
    def get_prompt(
        self,
        prompt_name: str,
        label: str | None = None,
        version: int | None = None,
        fallback_path: Path | None = None,
    ) -> PromptResult:
        """
        Fetch prompt with environment awareness.

        Args:
            prompt_name: Name in Langfuse
            label: Environment label (production, staging, dev)
            version: Specific version (overrides label)
            fallback_path: Local file if Langfuse unavailable
        """
        if version is not None:
            # Explicit version takes precedence
            prompt = self.langfuse.get_prompt(prompt_name, version=version)
        elif label is not None:
            # Label-based fetch
            prompt = self.langfuse.get_prompt(prompt_name, label=label)
        else:
            # Default: production label
            prompt = self.langfuse.get_prompt(prompt_name, label="production")

        return PromptResult(
            content=prompt.prompt,
            source="langfuse",
            version=prompt.version,
            name=prompt_name,
        )
```

### Metadata Tracking

```python
# Track which version generated the report
def get_prompt_metadata(self) -> dict:
    """Return metadata for observability."""
    return {
        "prompt_name": self.prompt_result.name,
        "prompt_version": self.prompt_result.version,
        "prompt_source": self.prompt_result.source,
    }
```

---

## Rollback Procedures

### Quick Rollback (Label Move)

```python
# In Langfuse UI or API:
# Move 'production' label from v4 back to v3

# Code automatically uses v3 (no deployment needed)
prompt = langfuse.get_prompt("dr-report-main", label="production")
# → Returns v3
```

### Rollback Checklist

1. [ ] Identify last known good version
2. [ ] Move `production` label to that version in Langfuse UI
3. [ ] Verify in logs that new requests use old version
4. [ ] Investigate root cause of issue
5. [ ] Create fixed version when ready
6. [ ] Repeat promotion flow

---

## File Fallback Strategy

When Langfuse is unavailable:

```python
# src/integrations/prompt_service.py
def get_prompt(self, prompt_name: str, ...) -> PromptResult:
    try:
        return self._fetch_from_langfuse(prompt_name, label, version)
    except LangfuseError as e:
        logger.warning(f"Langfuse unavailable: {e}")

        if fallback_path and fallback_path.exists():
            content = fallback_path.read_text()
            return PromptResult(
                content=content,
                source="file",
                version=0,  # Unknown version
                name=prompt_name,
            )

        raise PromptNotFoundError(f"No fallback for {prompt_name}")
```

### Fallback File Location

```
src/report/prompt_templates/
├── th/
│   └── single-stage/
│       └── main_prompt_v4_minimal.txt  # Fallback for dr-report-main
```

---

## Version Naming Conventions

### Prompt Names

```
{domain}-{component}-{variant}

Examples:
- dr-report-main           # Main DR report prompt
- dr-report-technical      # Technical analysis section
- dr-report-news           # News summary section
```

### Version Comments

When creating versions in Langfuse, include:

```
v5: Added few-shot examples for volatile market conditions
v4: Simplified system prompt, reduced token usage
v3: Fixed Thai language formatting issues
```

---

## References

- [SKILL.md](SKILL.md) - Overview
- [AB-TESTING.md](AB-TESTING.md) - A/B testing patterns
- [OBSERVABILITY.md](OBSERVABILITY.md) - Tracking and metrics
- [Langfuse Versioning Docs](https://langfuse.com/docs/prompts/get-started#versioning)
