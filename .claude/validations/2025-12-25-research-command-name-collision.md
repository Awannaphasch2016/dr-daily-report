# Validation Report

**Claim**: "/research still doesn't work - does Claude have reserved words for slash commands?"
**Type**: hypothesis (name collision investigation)
**Date**: 2025-12-25

---

## Status: ✅ TRUE (Partially)

Claude Code **does have reserved names** - not exactly "reserved words" but **naming collisions** between skills and commands.

---

## Evidence Summary

### Root Cause Identified

**Name Collision Between Skill and Command**

1. **Existing Research Skill**
   - Location: `.claude/skills/research/SKILL.md`
   - Name field: `name: research`
   - Purpose: "Systematic investigation and root cause analysis"
   - Type: **Skill** (auto-invoked by Claude, not user-invocable)
   - Created: 2025-12-23 (before command was created)

2. **New Research Command**
   - Location: `.claude/commands/research.md`
   - Name field: `name: research`
   - Purpose: "Divergent solution exploration"
   - Type: **Command** (should be user-invocable)
   - Created: 2025-12-25 (this session)

3. **Conflict Evidence**
   ```bash
   $ grep -r "^name: research" .claude/
   .claude/skills/research/SKILL.md:name: research
   .claude/commands/research.md:name: research
   ```

### How Claude Code Resolves Name Collisions

**Priority order** (inferred from behavior):
1. **Skills** take precedence (auto-invoked by Claude)
2. **Commands** are secondary (user-invoked)

When user types `/research`:
- Claude Code finds **both** skill and command with `name: research`
- Chooses skill (higher priority)
- Skill error message: "This slash command can only be invoked by Claude"
- **Command is never reached**

### Evidence from Error Message

Error: "This slash command can only be invoked by Claude, not directly by users."

**Analysis**:
- This is the **skill's error message** (skills are Claude-only)
- NOT a generic "command not found" error
- Proves: Claude Code is seeing the skill, not the command

### Contradicting Evidence (Configuration is Correct)

The **command configuration is valid**:
- ✅ YAML frontmatter present
- ✅ All required fields (`name`, `accepts_args`, `arg_schema`)
- ✅ Matches pattern of working commands
- ✅ File in correct location

**But** it doesn't matter because the skill takes precedence.

---

## Analysis

### Overall Assessment

The claim is **TRUE**: Claude Code has implicit "reserved names" through **naming collisions**.

While not technically "reserved words" in the language sense, certain names are **effectively reserved** because they're already taken by:
- Skills (`.claude/skills/*/SKILL.md`)
- Potentially built-in commands
- Project-specific hooks

### Key Findings

**Finding 1**: Name collision between skill and command
- **Significance**: Skills have priority over commands
- **Impact**: Command is unreachable with name "research"
- **Evidence**: Both files have `name: research`, error shows skill behavior

**Finding 2**: Skills vs Commands have different invocation models
- **Skills**: Auto-invoked by Claude (not user-callable)
- **Commands**: User-invoked (explicitly called with `/command`)
- **Collision**: When names match, skill wins

**Finding 3**: YAML frontmatter was correct all along
- **Previous hypothesis**: Missing YAML was the issue
- **Actual issue**: Name collision, not configuration
- **Lesson**: Configuration can be perfect but still not work due to namespace conflicts

### Confidence Level: High

**Reasoning**:
- ✅ Direct evidence: Both files exist with same name
- ✅ Error message matches skill behavior
- ✅ Reproducible: Happens every time
- ✅ Logical: Name collision explains all symptoms

---

## Recommendations

### Fix: Rename the Command

**Option 1: /explore** (Recommended)
- Emphasizes exploration phase
- Short, clear, no conflicts
- Example: `/explore "How to implement X"`

**Option 2: /alternatives**
- Emphasizes comparing alternatives
- Descriptive but longer
- Example: `/alternatives "State management library"`

**Option 3: /evaluate**
- Emphasizes evaluation matrix
- Clear action verb
- Example: `/evaluate "API design approaches"`

**Option 4: /solutions**
- Emphasizes solution space exploration
- Plural suggests multiple options
- Example: `/solutions "How to cache data"`

**Option 5: /diverge**
- Matches the diverge/converge pattern
- Technical but accurate
- Pairs with `/specify` (converge)
- Example: `/diverge "Backend architecture"`

### Implementation Steps

1. **Rename command file**:
   ```bash
   mv .claude/commands/research.md .claude/commands/explore.md
   ```

2. **Update YAML frontmatter**:
   ```yaml
   ---
   name: explore  # Changed from 'research'
   description: Systematically explore ALL potential solutions...
   accepts_args: true
   arg_schema:
     - name: goal
       required: true
     - name: focus
       required: false
   composition: []
   ---
   ```

3. **Update documentation**:
   - `.claude/commands/README.md` - Change `/research` to `/explore`
   - Any references in other command files

4. **Test the renamed command**:
   ```bash
   /explore "How to verify a command works"
   ```

### Alternative: Rename the Skill Instead

If you prefer to keep `/research` as the command name:

1. **Rename skill directory**:
   ```bash
   mv .claude/skills/research .claude/skills/investigation
   ```

2. **Update skill SKILL.md**:
   ```yaml
   ---
   name: investigation  # Changed from 'research'
   description: Systematic investigation and root cause analysis...
   ---
   ```

**Trade-off**:
- ✅ Keeps `/research` command name (matches diverge/converge pattern)
- ❌ Breaks any code/docs referencing the skill
- ❌ "Research" skill name is more intuitive than command

---

## Next Steps

- [ ] Choose new command name (recommend: `/explore`)
- [ ] Rename `.claude/commands/research.md` → `.claude/commands/{new-name}.md`
- [ ] Update `name:` field in YAML frontmatter
- [ ] Update `.claude/commands/README.md` documentation
- [ ] Test renamed command: `/{new-name} "test query"`
- [ ] Verify no "can only be invoked by Claude" error
- [ ] Document decision in `/journal`

---

## Lesson Learned

**Name Uniqueness Principle**: Command and skill names must be unique across **all** `.claude/` directories.

**Before creating new commands/skills**:
```bash
# Check if name is already taken
grep -r "^name: {new-name}" .claude/
```

**Namespace partitioning**:
- Skills: Investigation, debugging, research tasks
- Commands: User-facing workflows, orchestration
- Keep names distinct to avoid collisions

---

## References

**Files involved**:
- `.claude/skills/research/SKILL.md` - Existing skill (created first)
- `.claude/commands/research.md` - New command (name collision)
- `.claude/bug-hunts/2025-12-25-research-command-blocked.md` - Previous investigation (missed this issue)

**Error**:
```
/research
This slash command can only be invoked by Claude, not directly by users.
```

**Evidence**:
```bash
$ grep -r "^name: research" .claude/
.claude/skills/research/SKILL.md:name: research
.claude/commands/research.md:name: research
```

---

## Conclusion

**Status**: ✅ **TRUE**

Claude Code **does** have effectively reserved names through **namespace collisions**. The name "research" was already taken by an existing skill, preventing the command from being accessible.

**Fix**: Rename command to `/explore`, `/alternatives`, `/evaluate`, `/solutions`, or `/diverge`.

**Recommended**: `/explore` (short, clear, matches purpose)
