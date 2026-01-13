# Tuple Kernel Architecture

**Purpose**: Define the Thinking Tuple as the universal cognitive kernel for all reasoning operations.

**Core Insight**: The Thinking Tuple is the OS; commands are apps running on it.

---

## 1. The Universal Kernel Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER PROMPT (any)                               │
│                    (slash command or plain text)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TUPLE ROUTER                                   │
│                                                                         │
│  1. Classify intent (goal, exploration, verification, etc.)             │
│  2. Select default Strategy if no explicit command                      │
│  3. Instantiate or update Thinking Tuple                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        THINKING TUPLE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │ Constraints │  │  Invariant  │  │ Principles  │                     │
│  │             │  │             │  │             │                     │
│  │ • Context   │  │ • Success   │  │ • Tier-0    │                     │
│  │ • Specs     │  │   criteria  │  │ • Task-     │                     │
│  │ • Resources │  │ • What must │  │   specific  │                     │
│  │ • Learned   │  │   be true   │  │   clusters  │                     │
│  └─────────────┘  └─────────────┘  └─────────────┘                     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         STRATEGY                                 │   │
│  │                                                                  │   │
│  │  [                                                               │   │
│  │    { mode: "/decompose", prompt: "break the problem" },          │   │
│  │    { mode: "/explore",   prompt: "find alternatives" },          │   │
│  │    { mode: "/consolidate", prompt: "synthesize decision" }       │   │
│  │  ]                                                               │   │
│  │                                                                  │   │
│  │  Each mode = command as first-class function                     │   │
│  │  Pipeline executes sequentially, updating tuple state            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────┐                                                       │
│  │    Check    │ ← Evaluate after Strategy completes                   │
│  │             │                                                       │
│  │ • Evidence  │   If insufficient:                                    │
│  │   Layers    │   • Extend Strategy with more modes                   │
│  │ • Local     │   • Or spin new tuple with updated Constraints        │
│  │   criteria  │                                                       │
│  └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT                                       │
│                                                                         │
│  Result of Strategy execution, verified against Invariant               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tuple Router: Intent Classification

The router classifies any prompt (slash or plain) and selects default Strategy:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TUPLE ROUTER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: "Fix the Lambda timeout bug"                                    │
│                                                                         │
│  CLASSIFICATION:                                                        │
│  ├── Contains action verb (fix, build, deploy)? → Goal-oriented         │
│  ├── Contains question (what, why, how)?        → Explanation           │
│  ├── Contains "compare", "vs", "or"?            → Comparison            │
│  ├── Contains "is X correct", "verify"?         → Verification          │
│  └── Default                                    → Goal-oriented         │
│                                                                         │
│  SELECTED STRATEGY: [/step "Fix the Lambda timeout bug"]                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

ROUTING TABLE:

┌──────────────────────┬─────────────────────┬───────────────────────────┐
│ Intent Pattern       │ Detected By         │ Default Strategy          │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Goal-oriented        │ Action verbs:       │ [/step]                   │
│                      │ fix, build, deploy, │                           │
│                      │ add, implement      │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Exploration          │ "what are options"  │ [/explore]                │
│                      │ "how could we"      │                           │
│                      │ "alternatives"      │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Explanation          │ "how does X work"   │ [/understand]             │
│                      │ "explain X"         │                           │
│                      │ "what is X"         │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Verification         │ "is X correct"      │ [/validate]               │
│                      │ "verify that"       │                           │
│                      │ "check if"          │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Comparison           │ "X vs Y"            │ [/what-if]                │
│                      │ "compare X and Y"   │                           │
│                      │ "X or Y"            │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Causal Analysis      │ "why did X happen"  │ [/trace]                  │
│                      │ "what caused X"     │                           │
│                      │ "root cause of"     │                           │
├──────────────────────┼─────────────────────┼───────────────────────────┤
│ Explicit Command     │ /command "prompt"   │ [/command as specified]   │
│                      │                     │                           │
└──────────────────────┴─────────────────────┴───────────────────────────┘
```

---

## 3. Commands as Strategy Modes

Each command is a **mode** that can be invoked within Strategy:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      COMMAND MODE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  MODE INTERFACE:                                                        │
│                                                                         │
│  interface Mode {                                                       │
│    name: string;           // e.g., "/explore"                          │
│    type: ModeType;         // divergent | convergent | verify | ...     │
│    tupleEffects: {                                                      │
│      constraints: "expand" | "refine" | "none";                         │
│      invariant: "refine" | "test" | "none";                             │
│      principles: "add" | "none";                                        │
│    };                                                                   │
│    localCheck: Checklist;  // Mode-specific completion criteria         │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

MODE CATALOG:

┌────────────────┬──────────────┬─────────────────────────────────────────┐
│ Command        │ Mode Type    │ Tuple Effects                           │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /step          │ goal_oriented│ Full control over entire tuple          │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /explore       │ divergent    │ Constraints: +alternatives              │
│                │              │ Principles: +discovered heuristics      │
│                │              │ Check: coverage criteria                │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /understand    │ clarify      │ Invariant: +understanding criteria      │
│                │              │ Check: clarity assessment               │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /validate      │ verify       │ Invariant: test against evidence        │
│                │              │ Check: +confidence annotation           │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /what-if       │ compare      │ Constraints: +scenario alternatives     │
│                │              │ Check: trade-off analysis               │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /consolidate   │ converge     │ Constraints: synthesize to decision     │
│                │              │ Check: coherence assessment             │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /trace         │ causal       │ Constraints: +causal chain              │
│                │              │ Check: root cause identified            │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /decompose     │ decompose    │ Invariant: break into sub-invariants    │
│                │              │ Check: exhaustive breakdown             │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /invariant     │ scan         │ Check: evaluate against specification   │
│                │              │ Output: delta (violations count)        │
├────────────────┼──────────────┼─────────────────────────────────────────┤
│ /reconcile     │ fix          │ Actions: fix violations                 │
│                │              │ Check: delta = 0                        │
└────────────────┴──────────────┴─────────────────────────────────────────┘
```

---

## 4. Strategy Execution: Pipeline Model

Strategy is a pipeline of modes. Each mode:
1. Receives current tuple state
2. Executes (using Claude's innate behavior)
3. Updates tuple state
4. Passes to next mode

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      STRATEGY EXECUTION FLOW                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INITIAL TUPLE STATE:                                                   │
│  ├── Constraints: { problem: "Lambda timeout" }                         │
│  ├── Invariant: "Problem solved"                                        │
│  ├── Principles: [Tier-0]                                               │
│  └── Check: null                                                        │
│                                                                         │
│  STRATEGY: [                                                            │
│    { mode: "/decompose", prompt: "break into sub-problems" },           │
│    { mode: "/explore",   prompt: "find solutions for each" },           │
│    { mode: "/validate",  prompt: "test assumptions" },                  │
│    { mode: "/consolidate", prompt: "synthesize solution" }              │
│  ]                                                                      │
│                                                                         │
│                          EXECUTION                                      │
│                              │                                          │
│  ┌───────────────────────────┴───────────────────────────┐             │
│  │                                                        │             │
│  │  MODE 1: /decompose                                    │             │
│  │  ├── Input: Tuple state                                │             │
│  │  ├── Execute: Break problem into parts                 │             │
│  │  ├── Update: Invariant → [sub-inv-1, sub-inv-2, ...]   │             │
│  │  └── Output: Updated tuple                             │             │
│  │                                                        │             │
│  │                    ↓                                   │             │
│  │                                                        │             │
│  │  MODE 2: /explore                                      │             │
│  │  ├── Input: Updated tuple                              │             │
│  │  ├── Execute: Find solutions for each sub-problem      │             │
│  │  ├── Update: Constraints += alternatives               │             │
│  │  └── Output: Updated tuple                             │             │
│  │                                                        │             │
│  │                    ↓                                   │             │
│  │                                                        │             │
│  │  MODE 3: /validate                                     │             │
│  │  ├── Input: Updated tuple                              │             │
│  │  ├── Execute: Test key assumptions                     │             │
│  │  ├── Update: Check += confidence annotations           │             │
│  │  └── Output: Updated tuple                             │             │
│  │                                                        │             │
│  │                    ↓                                   │             │
│  │                                                        │             │
│  │  MODE 4: /consolidate                                  │             │
│  │  ├── Input: Updated tuple                              │             │
│  │  ├── Execute: Synthesize decision                      │             │
│  │  ├── Update: Constraints → final decision              │             │
│  │  └── Output: Final tuple                               │             │
│  │                                                        │             │
│  └────────────────────────────────────────────────────────┘             │
│                              │                                          │
│                              ▼                                          │
│                                                                         │
│  FINAL CHECK:                                                           │
│  ├── Evaluate: Does final state satisfy Invariant?                      │
│  ├── If YES: Return result                                              │
│  └── If NO: Extend Strategy or spin new tuple                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Check Loop: Bounded Error

The Check phase provides bounded error by catching failures before they propagate:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CHECK LOOP                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  After Strategy execution:                                              │
│                                                                         │
│       ┌─────────────────────────┐                                       │
│       │   Evaluate Invariant    │                                       │
│       │                         │                                       │
│       │   Using Evidence:       │                                       │
│       │   • Layer 1 (surface)   │                                       │
│       │   • Layer 2 (content)   │                                       │
│       │   • Layer 3 (observe)   │                                       │
│       │   • Layer 4 (ground)    │                                       │
│       └───────────┬─────────────┘                                       │
│                   │                                                     │
│         ┌────────┴────────┐                                            │
│         ▼                 ▼                                            │
│   ┌──────────┐      ┌──────────┐                                       │
│   │ SATISFIED│      │   NOT    │                                       │
│   │          │      │SATISFIED │                                       │
│   └────┬─────┘      └────┬─────┘                                       │
│        │                 │                                              │
│        ▼                 ▼                                              │
│   ┌──────────┐      ┌──────────────────────────────────┐               │
│   │  RETURN  │      │         RECOVERY OPTIONS          │               │
│   │  RESULT  │      │                                   │               │
│   └──────────┘      │  1. Extend Strategy:              │               │
│                     │     Add more modes to pipeline    │               │
│                     │     e.g., [/explore, /validate]   │               │
│                     │                                   │               │
│                     │  2. Spin New Tuple:               │               │
│                     │     Update Constraints with       │               │
│                     │     what was learned              │               │
│                     │     Reset Strategy                │               │
│                     │                                   │               │
│                     │  3. Escape Hatch:                 │               │
│                     │     If stuck, report failure      │               │
│                     │     with diagnostic info          │               │
│                     └──────────────────────────────────┘               │
│                                                                         │
│  ERROR BOUND:                                                           │
│  ├── Without Check: error accumulates over all steps                    │
│  └── With Check: error bounded to single tuple, caught at Check         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Internal Modes (Micro-Operations)

Beyond slash commands, internal modes handle micro-operations:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INTERNAL MODES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  These modes are invoked implicitly within larger operations:           │
│                                                                         │
│  ┌────────────────────┬───────────────────────────────────────────────┐│
│  │ Mode               │ Purpose                                       ││
│  ├────────────────────┼───────────────────────────────────────────────┤│
│  │ summarize          │ Compress content while preserving meaning     ││
│  │ rewrite_simple     │ Reduce complexity of text                     ││
│  │ extract_criteria   │ Pull out evaluation axes from context         ││
│  │ compare_two        │ Binary comparison of two options              ││
│  │ verify_claim       │ Quick claim verification                      ││
│  │ format_output      │ Structure output for readability              ││
│  └────────────────────┴───────────────────────────────────────────────┘│
│                                                                         │
│  EXAMPLE USAGE:                                                         │
│                                                                         │
│  Strategy = [                                                           │
│    { mode: "/explore", prompt: "find options" },                        │
│    { mode: "summarize", prompt: "compress findings" },  ← internal     │
│    { mode: "/validate", prompt: "test assumptions" },                   │
│    { mode: "format_output", prompt: "structure result" } ← internal    │
│  ]                                                                      │
│                                                                         │
│  Internal modes:                                                        │
│  • Don't need explicit slash command                                    │
│  • Use Claude's innate behavior directly                                │
│  • Are composable within Strategy pipeline                              │
│  • Have minimal overhead (no full tuple ceremony)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Integration with Specifications

The tuple kernel integrates with spec-driven development:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TUPLE + SPECIFICATIONS                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  When working on an objective (linebot, telegram):                      │
│                                                                         │
│  1. LOAD SPECIFICATION:                                                 │
│     ├── .claude/specs/{objective}/spec.yaml                             │
│     ├── .claude/specs/{objective}/invariants.md                         │
│     └── .claude/specs/{objective}/constraints.md                        │
│                                                                         │
│  2. POPULATE TUPLE:                                                     │
│     ├── Constraints: spec constraints + learned constraints             │
│     ├── Invariant: spec invariants (5 levels)                           │
│     ├── Principles: Tier-0 + objective-specific                         │
│     └── Check: spec acceptance criteria                                 │
│                                                                         │
│  3. EXECUTE STRATEGY:                                                   │
│     └── Strategy modes operate on spec-populated tuple                  │
│                                                                         │
│  4. VERIFY AGAINST SPEC:                                                │
│     └── Check evaluates against spec invariants                         │
│                                                                         │
│  5. UPDATE CONVERGENCE STATE:                                           │
│     └── .claude/state/convergence/{objective}.yaml                      │
│                                                                         │
│  FLOW:                                                                  │
│                                                                         │
│  Spec ──────────────▶ Tuple ──────────────▶ Strategy ──────────────▶   │
│  (ground truth)       (runtime state)       (execution)                 │
│                                                                         │
│       ◀────────────── Check ◀──────────────────────────────────────    │
│       (update spec)   (verify against spec)                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Key Benefits

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        KEY BENEFITS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. UNIVERSALITY                                                        │
│     ├── Every prompt goes through tuple                                 │
│     ├── No fragmentation between commands and plain prompts             │
│     └── Consistent cognitive architecture                               │
│                                                                         │
│  2. BOUNDED ERROR                                                       │
│     ├── Check catches failures before propagation                       │
│     ├── Error ∝ check frequency, not step count                         │
│     └── Long-running agents remain correct                              │
│                                                                         │
│  3. COMPOSABILITY                                                       │
│     ├── Commands as first-class functions                               │
│     ├── Strategy pipelines chain modes                                  │
│     └── Complex reasoning = mode composition                            │
│                                                                         │
│  4. DEBUGGABILITY                                                       │
│     ├── Tuple state is traceable                                        │
│     ├── Can inspect Constraints, Invariant, Strategy at any point       │
│     └── Failure diagnosis: "Which mode failed? What was Check?"         │
│                                                                         │
│  5. TRANSFERABILITY                                                     │
│     ├── Pattern works for any LLM capable of reasoning                  │
│     ├── Not Claude-specific                                             │
│     └── Universal cognitive framework                                   │
│                                                                         │
│  6. TEACHABILITY                                                        │
│     ├── "Always tuple" is simpler than "which tier?"                    │
│     ├── One mental model for all reasoning                              │
│     └── Commands are just specialized modes                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. See Also

- [CLAUDE.md - Principle #26](.claude/CLAUDE.md#26-thinking-tuple-protocol-universal-kernel)
- [CLAUDE.md - Principle #27](.claude/CLAUDE.md#27-commands-as-strategy-modes)
- [Thinking Tuple Guide](docs/guides/thinking-tuple-protocol.md)
- [Specifications](.claude/specs/)
- [Command Mode Specifications](.claude/commands/README.md)

---

*Architecture: Tuple Kernel*
*Created: 2026-01-13*
