# Evolution: /problem-statement Command Implementation

**Date**: 2026-01-04
**Type**: Command Creation
**Status**: ✅ Complete

---

## Context

**User pain point**: "Sometimes there is no bug, but Claude asks for my decision or input to make progress. Honestly, most of the time, I don't know what the problem statement is. I need a slash command to recap the exact problems that may not be a bug and find relevant context then restate or explain to me so I have all the information enough to make decision."

**Problem**: When conversations span multiple sessions or become complex, users lose context about why they're being asked to make decisions. Claude asks "Which approach should we use?" but the user doesn't remember:
- What the original goal was
- How we got to this decision point
- What constraints or requirements exist
- What the trade-offs are between options

**Solution**: Create `/problem-statement` command that reconstructs complete decision context.

---

## Analysis Summary

### Redundancy Check

**Question**: Is /problem-statement redundant with existing commands?

**Comparison with existing commands**:

| Command | Purpose | Overlap with /problem-statement |
|---------|---------|----------------------------------|
| `/reflect` | Analyze what you did and why | No - reflects on past actions, doesn't reconstruct decision context |
| `/trace` | Root cause analysis | No - traces failures backward, doesn't explain decision points |
| `/hypothesis` | Generate alternative explanations | No - generates hypotheses for failures, doesn't explain decisions |
| `/context` | Load context for task | No - loads file context, doesn't explain decision points |
| `/summary` | Summarize conversation | No - chronological summary, doesn't restructure around decision |
| `/explain` | Explain code/concept | No - explains technical concepts, not decision context |

**Conclusion**: NOT redundant. Fills critical gap.

### Name Clarity

**Question**: Is "/problem-statement" ambiguous?

**Analysis**:
- "Problem statement" is well-understood term (clear goal articulation)
- Matches user's intent exactly ("I need to understand what the problem is")
- Not confusing with other commands
- Command name clearly indicates purpose

**Conclusion**: Name is clear and appropriate.

### Priority Assessment

**User impact**: HIGH
- Directly addresses expressed pain point
- Improves decision-making quality (user has full context)
- Reduces back-and-forth ("wait, why are we choosing this?")
- Enables better collaboration (user and Claude aligned on problem)

**Implementation complexity**: MEDIUM
- Requires conversation analysis (scan recent messages)
- Requires timeline reconstruction (trace back to origin)
- Requires context gathering (constraints, requirements, trade-offs)
- Requires structured presentation (decision framework)

**Recommendation**: CREATE /problem-statement command (HIGH PRIORITY)

---

## Implementation

### Command File

**Created**: `.claude/commands/problem-statement.md` (~800 lines)

**Structure**:
- Command metadata (name, description, accepts_args)
- Quick Reference (example usage)
- 5-phase execution flow
- Comprehensive output format
- Examples (caching decision, architecture decision)
- Integration with other commands
- Best practices
- Prompt template

### 5-Phase Workflow

#### Phase 1: Identify Current Decision Point
**Purpose**: Find where conversation is blocked on user input

**Method**:
- Scan recent messages for questions to user
- Identify blocked progress indicators
- Extract alternative presentations
- Locate specific decision request

**Output**:
```
Decision type: Technology choice
Specific question: "Should we use Redis or DynamoDB for caching?"
Context: Blocked on cache implementation
```

#### Phase 2: Trace Problem Origin
**Purpose**: Build timeline from initial request to current decision

**Method**:
- Trace conversation backward chronologically
- Identify key milestones (problem identified, analysis done, options narrowed)
- Show progression of understanding

**Output**:
```
Timeline:
Message 10: User requested "faster API responses"
Message 25: Claude identified caching as solution
Message 40: Claude narrowed to Redis vs DynamoDB
Message 50: Claude asked user to choose (CURRENT)

Key progression:
Original problem (slow API) → Solution space (caching) → Specific choice (Redis vs DynamoDB)
```

#### Phase 3: Gather Relevant Context
**Purpose**: Collect all information needed to understand decision

**Method**:
- Extract constraints (budget, timeline, technical)
- List requirements (functional, performance, operational)
- Identify trade-off dimensions
- Note previous related decisions
- List assumptions made

**Output**:
```
Constraints:
- Budget: $100/month for infrastructure
- Timeline: Need decision this week to proceed
- Technical: Must integrate with existing Aurora database

Requirements:
- Functional: Cache 10,000 records
- Performance: <10ms latency
- Operational: Minimal ops overhead (small team)

Previous decisions:
- Decided to use Aurora (not external DB)
- Decided to cache precomputed data (not compute on-demand)
```

#### Phase 4: Restate Problem Clearly
**Purpose**: Articulate problem in simple, clear language

**Method**:
- State original goal
- Describe current situation
- Identify specific problem
- Explain why decision is needed
- Describe impact of decision

**Output**:
```
**Original goal**: Make API responses faster
**Current situation**: Identified caching as solution, need to choose technology
**Specific problem**: Need to choose between Redis vs DynamoDB
**Why decision needed**: Blocks cache implementation (2-week task)
**Impact**: Delays API performance improvement

**In short**: Choose cache technology to make API faster
```

#### Phase 5: Present Decision Framework
**Purpose**: Structure decision with all options and trade-offs

**Method**:
- List all options with descriptions
- For each option: pros, cons, best for, not good for
- Provide comparison matrix with criteria
- Include recommendations (if applicable)

**Output**:
```
## Option 1: Redis
**Description**: In-memory cache, <1ms latency
**Pros**: ⚡ Fast, Rich data structures, Proven at scale
**Cons**: 💰 Higher cost ($50-150/month), Operational complexity
**Best for**: Need sub-5ms latency, already have Redis expertise
**Not good for**: Budget constrained, want minimal ops overhead

## Option 2: DynamoDB
**Description**: Managed NoSQL, 5-10ms latency
**Pros**: 💰 Lower cost ($10-30/month), Zero ops overhead, Auto-scaling
**Cons**: ⏱️ Slower (5-10ms), Less flexible queries
**Best for**: Budget constrained, want minimal ops, AWS-native stack
**Not good for**: Need sub-5ms latency, complex query patterns

## Comparison Matrix
| Criterion | Redis | DynamoDB | Winner |
|-----------|-------|----------|--------|
| Latency | <1ms | 5-10ms | Redis |
| Cost | $50-150 | $10-30 | DynamoDB |
| Ops Complexity | High | Low | DynamoDB |
| Weighted Score | 7/10 | 8/10 | DynamoDB |
```

### Integration with Other Commands

**`/problem-statement` → `/architect`**:
- Problem statement identifies architectural decision needed
- Use /architect to analyze architecture trade-offs
- Feed architecture analysis back into decision framework

**`/problem-statement` → `/check-principles`**:
- Problem statement reveals which principles apply
- Use /check-principles to verify compliance
- Include principle compliance in decision criteria

**`/problem-statement` → `/reflect`**:
- After making decision, use /reflect to analyze process
- Identify if /problem-statement helped decision quality
- Detect if any context was still missing

**Other commands → `/problem-statement`**:
- Any command that asks for user decision can trigger /problem-statement
- User runs /problem-statement when confused about why decision is needed
- Reconstruct context lost during long conversations

### Examples Included

#### Example 1: Caching Technology Decision
**Scenario**: Choosing between Redis and DynamoDB for API caching

**Demonstrates**:
- Technology choice decision point
- Budget and performance constraints
- Trade-off analysis (latency vs cost vs ops complexity)
- Comparison matrix with weighted scoring

#### Example 2: Architecture Pattern Decision
**Scenario**: Choosing between synchronous and event-driven architecture

**Demonstrates**:
- Architecture decision point
- System requirements and constraints
- Pattern trade-offs (complexity vs scalability vs debugging)
- Long-term implications

---

## Key Features

### 1. Context Reconstruction
**Problem**: User doesn't remember why decision is needed
**Solution**: Timeline showing progression from original request to current decision point

### 2. Complete Information Gathering
**Problem**: Missing constraints or requirements when making decision
**Solution**: Systematic gathering of constraints, requirements, trade-offs, assumptions, previous decisions

### 3. Clear Problem Articulation
**Problem**: Unclear what the actual problem is ("Why am I choosing this?")
**Solution**: Restate problem in 5 parts (original goal, current situation, specific problem, why needed, impact)

### 4. Structured Decision Framework
**Problem**: Options presented without clear comparison
**Solution**: For each option, provide pros/cons/best-for/not-good-for, plus comparison matrix

### 5. Integration with Workflow
**Problem**: Command exists in isolation
**Solution**: Clear integration with /architect, /check-principles, /reflect

---

## Benefits

### For Users

**Before /problem-statement**:
```
Claude: "Should we use Redis or DynamoDB?"
User: "Uh... I don't remember why we need caching. What was the original problem?"
Claude: [User has to scroll back through 50 messages to understand context]
```

**After /problem-statement**:
```
Claude: "Should we use Redis or DynamoDB?"
User: "/problem-statement"
Claude: [Provides complete context]
- Original goal: Make API faster
- Current situation: Narrowed to Redis vs DynamoDB
- Constraints: $100/month budget, need <10ms latency
- Option 1: Redis (faster but expensive)
- Option 2: DynamoDB (slower but cheaper)
- Comparison: DynamoDB wins (8/10 vs 7/10)
User: "Ah, now I understand. Let's go with DynamoDB."
```

**Impact**:
- ✅ Better decision quality (full context available)
- ✅ Faster decision making (no scrolling back through conversation)
- ✅ Reduced confusion (clear problem articulation)
- ✅ Improved collaboration (user and Claude aligned)

### For Development Workflow

**Use cases**:
1. **Long conversations**: Context lost over multiple sessions
2. **Complex decisions**: Multiple constraints and trade-offs to consider
3. **Architecture choices**: Need to understand implications of each option
4. **Technology selection**: Need to compare technologies objectively
5. **Priority decisions**: Need to understand impact of choosing one task over another

**Integration points**:
- Run after `/architect` reveals decision needed
- Run before making deployment decisions
- Run when `/reflect` shows unclear decision process
- Run when user asks "why are we doing this?"

---

## Metrics

### Implementation
- **File created**: 1 (`.claude/commands/problem-statement.md`)
- **Lines of documentation**: ~800
- **Phases implemented**: 5
- **Examples provided**: 2 (comprehensive)

### Command Structure
- **Execution steps**: 5 phases
- **Output sections**: 10 (decision type, timeline, constraints, requirements, trade-offs, assumptions, problem statement, options, comparison, recommendations)
- **Integration points**: 3 commands (/architect, /check-principles, /reflect)
- **Use cases documented**: 8

---

## Validation

### User Need Alignment

**User's expressed need**: "I need slash command /problem-statement to recap the exact problems that may not be a bug and find relevant context then restate or explain to me so I have all the information enough to make decision."

**Command capabilities**:
- ✅ Recaps exact problems (Phase 4: Restate Problem Clearly)
- ✅ Finds relevant context (Phase 3: Gather Relevant Context)
- ✅ Restates and explains (Phase 4: Clear articulation)
- ✅ Provides all information for decision (Phase 5: Decision Framework)

**Alignment**: 100% match with user's expressed need

### Completeness Check

**Required elements for good decision-making**:
- ✅ What is the problem? (Phase 4)
- ✅ Why does it matter? (Phase 4: Impact)
- ✅ How did we get here? (Phase 2: Timeline)
- ✅ What are the constraints? (Phase 3: Constraints)
- ✅ What are the options? (Phase 5: Options)
- ✅ How do options compare? (Phase 5: Comparison Matrix)
- ✅ What is recommended? (Phase 5: Recommendations)

**Completeness**: All elements present

### Integration Validation

**Other commands can trigger /problem-statement**:
- ✅ /architect reveals decision needed → /problem-statement provides context
- ✅ /deploy blocked on user input → /problem-statement explains why
- ✅ /reflect shows unclear decision → /problem-statement reconstructs context

**Integration**: Properly connected with existing command ecosystem

---

## Anti-Patterns Prevented

### 1. Vague Decision Requests
**Before**: "Should we use approach A or B?"
**After**: Complete context with constraints, trade-offs, comparison matrix

### 2. Missing Context
**Before**: User doesn't remember original goal
**After**: Timeline from initial request to current decision

### 3. Unclear Trade-offs
**Before**: Options presented without comparison
**After**: Structured pros/cons and comparison matrix

### 4. No Recommendations
**Before**: User left to decide without guidance
**After**: Recommendations based on weighted criteria (when applicable)

---

## Future Enhancements

### Potential Phase 6: Historical Decisions
**Purpose**: Show similar past decisions and outcomes

**Method**:
- Search conversation history for similar decision points
- Extract what was chosen and why
- Note if outcome was successful or not
- Use as learning for current decision

**Example**:
```
## Similar Past Decisions

**Decision**: Cache technology (2 months ago)
**Chose**: In-memory dict (simplest option)
**Outcome**: ❌ Failed - didn't scale beyond 1000 records
**Lesson**: Simplicity isn't enough if it doesn't scale

**Apply to current decision**: Don't undervalue scalability
```

### Potential Phase 7: Decision Impact Simulation
**Purpose**: Simulate what happens after each choice

**Method**:
- For each option, project 1 month, 3 months, 6 months ahead
- Estimate impact on team (effort, complexity, maintenance)
- Estimate impact on system (performance, cost, reliability)
- Identify potential regret scenarios

**Example**:
```
## Decision Impact Simulation

**If choose Redis**:
- Month 1: Setup and integration (2 weeks effort)
- Month 3: Performance excellent (<1ms), ops burden moderate
- Month 6: Scaling issues (need to upgrade cluster), cost increasing
- Potential regret: "Wish we'd chosen managed solution"

**If choose DynamoDB**:
- Month 1: Setup and integration (1 week effort)
- Month 3: Performance good (5ms), zero ops burden
- Month 6: No scaling issues, cost stable
- Potential regret: "Wish we'd chosen faster option for critical paths"
```

---

## Related Work

### Related Commands
- `/reflect` - Metacognitive analysis of past actions
- `/trace` - Root cause analysis for failures
- `/hypothesis` - Generate alternative explanations
- `/architect` - Architecture analysis and trade-offs
- `/check-principles` - CLAUDE.md compliance audit

### Related Principles
- **Principle #2 (Progressive Evidence Strengthening)**: /problem-statement gathers all evidence levels for decision
- **Principle #9 (Feedback Loop Awareness)**: Helps users identify which loop type they're in
- **Principle #12 (OWL-Based Relationship Analysis)**: Uses formal comparison framework
- **Principle #20 (Execution Boundary Discipline)**: Identifies boundary-related decisions

### Related Documentation
- `.claude/diagrams/thinking-process-architecture.md` - Metacognitive framework
- `docs/RELATIONSHIP_ANALYSIS.md` - Formal comparison methods
- `.claude/CLAUDE.md` - Core principles

---

## Conclusion

**Status**: ✅ `/problem-statement` command fully implemented and production-ready

**Achievement**: Created command that directly addresses user pain point ("I don't know what the problem statement is") with comprehensive 5-phase workflow for decision context reconstruction.

**Impact**: Enables better decision-making by providing complete context (timeline, constraints, requirements, trade-offs, structured comparison) when users are asked to make choices.

**Integration**: Properly integrated with existing command ecosystem (/architect, /check-principles, /reflect) and aligned with CLAUDE.md principles.

**Next**: Command ready for use. No further implementation needed.
