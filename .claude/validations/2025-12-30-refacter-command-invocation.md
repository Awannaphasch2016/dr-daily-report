# Validation Report

**Claim**: "I can't execute /refacter or /refactor manually as claude slash command: > /refacter > This slash command can only be invoked by Claude, not directly by users. Ask Claude to run /refacter for you."

**Note**: Command has been renamed to `/restructure` after this validation was performed.

**Type**: `config` (command system configuration and invocation behavior)

**Date**: 2025-12-30

---

## Status: ⚠️ PARTIALLY TRUE

## Evidence Summary

**Supporting evidence** (2 items):

1. **Skill Tool Definition** (from system context):
   - Location: Tool invocation system
   - Data: Skill tool description states: "IMPORTANT: Only use Skill for skills listed in its user-invocable skills section"
   - Confidence: High
   - **Interpretation**: Some skills are marked as "user-invocable" while others are model-only

2. **Commands vs Skills Documentation**:
   - Location: `.claude/commands/README.md:13`
   - Data: "**Invocation** | Explicit (`/command-name`) | Auto-discovered by Claude"
   - Finding: Commands are described as "explicit" invocation
   - Confidence: Medium
   - **Note**: This suggests commands ARE user-invocable (contradicts claim)

**Contradicting evidence** (3 items):

1. **Command Frontmatter Structure**:
   - Location: `.claude/commands/restructure.md:1-13` (renamed from refacter.md)
   - Data:
     ```yaml
     ---
     name: restructure
     description: Analyze code complexity and hotspots...
     accepts_args: true
     arg_schema:
       - name: target
         required: true
     composition:
       - skill: refactor
     ---
     ```
   - Finding: **No `disable-model-invocation` or `model-only` flag present**
   - Confidence: High
   - **Impact**: Absence of restriction flag suggests command should be both user AND model invocable

2. **Web Research - Claude Code Slash Commands**:
   - Source: [Slash commands - Claude Code Docs](https://code.claude.com/docs/en/slash-commands)
   - Finding: "To prevent a specific slash command from becoming available to the model, add `disable-model-invocation: true` to the slash command's frontmatter"
   - **Key insight**: This implies commands are BOTH user and model invocable by DEFAULT
   - To make model-only: would need explicit flag (not present in `/restructure`)
   - Confidence: High

3. **Command Purpose Design**:
   - Location: `.claude/commands/README.md:5`
   - Data: "Slash commands provide direct **user control** over Claude's behavior"
   - Finding: Commands explicitly designed for user invocation
   - Confidence: High

**Missing evidence**:
- Cannot directly test user invocation (validation is running within Claude execution context)
- No official documentation stating which commands are model-only
- Error message source unclear (may be Claude Code UI behavior vs command definition)

---

## Analysis

### Overall Assessment

The claim appears to be **partially true but likely refers to SKILLS, not COMMANDS**:

**TRUE part**:
- Skills listed in the Skill tool are designated as either "user-invocable" or model-only
- The error message format matches Claude Code's skill invocation restrictions
- `/restructure` (formerly `/refacter`) references the `refacter` skill in its composition

**FALSE/MISLEADING part**:
- `/restructure` (formerly `/refacter`) is a **COMMAND**, not a skill
- Commands are documented as providing "direct user control"
- No `disable-model-invocation` flag in `/restructure` frontmatter
- Web research confirms commands are both user AND model invocable by default

### Key Findings

1. **Confusion between Skills and Commands**:
   - Skill: `refacter` (in `.claude/skills/refacter/`)
   - Command: `/restructure` (in `.claude/commands/restructure.md`, renamed from refacter.md)
   - The error message likely refers to attempting to invoke the SKILL directly, not the COMMAND

2. **Default Invocation Behavior**:
   - Commands: Both user and model invocable (unless `disable-model-invocation: true`)
   - Skills: Model-invoked by default, some marked as "user-invocable"

3. **Command Composition Pattern**:
   - `/restructure` command composes the `refacter` skill
   - When user invokes `/restructure`, command orchestrates skill invocation
   - Direct skill invocation (without command wrapper) may be restricted

### Confidence Level: Medium-High

**Reasoning**:
- Strong evidence that commands are user-invocable by design
- Missing direct testing capability (can't simulate user input)
- Error message wording suggests skill restriction, not command restriction
- Possible UI-level restriction not visible in file-based configuration

---

## Recommendations

**Current State: Command is likely user-invocable, but testing needed**

### For User:

1. **Verify command vs skill distinction**:
   - Commands (in `.claude/commands/`): User-invocable by design
   - Skills (in `.claude/skills/`): Model-invoked by default

2. **Test invocation scenarios**:
   ```bash
   # Try invoking the command directly (as user)
   /restructure src/

   # vs asking Claude to run it
   "Please analyze code complexity in src/"
   ```

3. **If command is truly model-only**:
   - This would be unusual based on documentation
   - Add `disable-model-invocation: false` explicitly to frontmatter
   - Or file issue with Claude Code if behavior doesn't match docs

### If Command Should Be User-Invocable (Recommended):

**No changes needed** - command appears correctly configured:
- Has `accepts_args: true`
- Has `arg_schema` defining user arguments
- No invocation restrictions in frontmatter
- Follows standard command pattern

### If Command Should Be Model-Only:

Add to frontmatter:
```yaml
---
name: refacter
disable-user-invocation: true  # If this field exists
# OR
model-only: true  # Check Claude Code docs for correct field name
---
```

**Note**: Current Claude Code documentation (v2.0.76) does not show a "model-only" flag for commands - only `disable-model-invocation` to prevent MODEL access.

---

## Next Steps

- [ ] Test user invocation of `/restructure` in Claude Code UI
- [ ] If user invocation fails, check Claude Code version requirements
- [ ] Review Skill tool definition for "user-invocable skills" list
- [ ] Consider documenting command vs skill invocation in `.claude/commands/README.md`
- [ ] If restriction is intentional, add explicit flag to frontmatter for clarity

---

## References

**Web Sources**:
- [Slash commands - Claude Code Docs](https://code.claude.com/docs/en/slash-commands)
- [Understanding Claude Code: Skills vs Commands vs Subagents vs Plugins](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins)
- [GitHub Issue #13115 - Consider merging Skills and Slash Commands](https://github.com/anthropics/claude-code/issues/13115)

**Codebase**:
- `.claude/commands/restructure.md:1-13` - Command frontmatter (renamed from refacter.md)
- `.claude/commands/README.md:5` - Command purpose statement
- `.claude/commands/README.md:13` - Commands vs Skills invocation comparison
- `.claude/skills/refacter/SKILL.md` - Skill definition (referenced by command)

**System Context**:
- Skill tool definition: "Only use Skill for skills listed in its user-invocable skills section"

**Claude Code**:
- Version: 2.0.76
- Help flag: `--disable-slash-commands` (confirms commands are normally enabled)

---

## Interpretation Note

The error message text:
> "This slash command can only be invoked by Claude, not directly by users. Ask Claude to run /refacter for you."

...suggests this may be:
1. A UI-level restriction in Claude Code that isn't reflected in file-based configuration
2. Confusion between skill invocation (model-only) vs command invocation (user-invocable)
3. A version-specific behavior in Claude Code 2.0.76
4. Expected behavior that conflicts with documentation

**Recommendation**: Treat as user-invocable based on configuration, but document any UI-level restrictions discovered through testing.
