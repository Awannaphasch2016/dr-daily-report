---
name: design
description: Domain-aware design command - create new solutions with domain-specific checklists and patterns
accepts_args: true
arg_schema:
  - name: domain
    required: false
    description: "Domain type (auto-detected if not provided): aws, python, api, schema, frontend"
  - name: goal
    required: true
    description: "What you want to design (e.g., 'VPC with Lambda', 'repository pattern for data access')"
composition:
  - skill: research
---

# Design Command

**Purpose**: Create new solutions with domain-specific thinking, checklists, and patterns.

**Core Philosophy**: "Design is creation with constraints" - unlike inspection (`/x-ray`), design produces something new. Domain awareness ensures appropriate patterns and checklists are applied.

**Naming rationale**: "Design" explicitly means creating something new, distinguishing from `/x-ray` (inspect existing) and `/analysis` (think about existing).

**When to use**:
- Creating new AWS infrastructure
- Designing Python code architecture
- Planning API endpoints
- Designing database schemas
- Building frontend components

**When NOT to use**:
- Understanding existing systems → use `/x-ray`
- Comparing alternatives → use `/what-if`
- Quick exploration → use `/explore`
- Porting from external sources → use `/adapt`

---

## Design vs Related Commands

| Command | Purpose | Output |
|---------|---------|--------|
| `/x-ray` | Inspect existing | Structure analysis |
| `/design` | Create new solutions | Design document |
| `/specify` | Quick design sketch | Lightweight spec |
| `/what-if` | Compare alternatives | Comparison analysis |
| `/explore` | Divergent exploration | Option evaluation |

**Workflow:**
```bash
/x-ray "current auth system"       # SEE what exists
/what-if "OAuth vs JWT"            # COMPARE alternatives
/design python "OAuth2 handler"    # CREATE new solution
```

**Design vs Specify:**
- `/specify` = Quick sketch, lightweight, exploratory
- `/design` = Thorough, domain-aware, implementation-ready

---

## Quick Reference

```bash
# AWS infrastructure design (domain auto-detected)
/design "VPC with private subnets for Lambda"
→ Domain: aws
→ Checklist: Security groups, NAT Gateway, VPC endpoints, IAM

# Python code design (domain auto-detected)
/design "Repository pattern for Aurora access"
→ Domain: python
→ Checklist: SOLID, type hints, error handling, testing

# API design (domain auto-detected)
/design "REST API for backtester"
→ Domain: api
→ Checklist: Endpoints, authentication, versioning, rate limiting

# Explicit domain override
/design aws "networking for multi-region deployment"
/design python "event sourcing implementation"
/design api "GraphQL schema for reports"
/design schema "user preferences storage"
/design frontend "chart component with WebSocket updates"
```

---

## Domain Detection

**Auto-detection from keywords:**

| Keywords | Domain |
|----------|--------|
| VPC, Lambda, S3, IAM, EC2, RDS, CloudWatch, Terraform | `aws` |
| class, function, module, pattern, SOLID, type, Python | `python` |
| REST, endpoint, API, route, HTTP, GraphQL, OpenAPI | `api` |
| table, column, schema, index, migration, foreign key | `schema` |
| component, React, UI, state, hook, CSS, frontend | `frontend` |

**Override:** Provide explicit domain as first argument:
```bash
/design python "event sourcing implementation"
```

---

## Execution Flow

### Phase 1: Parse Domain and Goal

```bash
# Auto-detect domain
/design "VPC with Lambda"
→ Keywords: VPC, Lambda → Domain: aws

# Explicit domain
/design python "repository pattern"
→ Domain: python (explicit)
```

### Phase 2: Apply Domain-Specific Checklist

Each domain has specific considerations:

---

## Domain: AWS Infrastructure

**Checklist:**

### Security
- [ ] IAM roles with least privilege
- [ ] Security groups (ingress/egress rules)
- [ ] VPC endpoints for AWS services (avoid NAT traversal)
- [ ] Encryption at rest and in transit
- [ ] Secrets management (Secrets Manager, not env vars)

### Networking
- [ ] VPC CIDR planning (non-overlapping)
- [ ] Public vs private subnets
- [ ] NAT Gateway vs VPC endpoints (cost/performance)
- [ ] Cross-region considerations
- [ ] DNS resolution (Route 53, VPC DNS)

### Compute
- [ ] Lambda memory/timeout sizing
- [ ] Cold start mitigation (provisioned concurrency?)
- [ ] Container image vs ZIP deployment
- [ ] Concurrency limits

### Storage
- [ ] Aurora vs DynamoDB vs S3 (access patterns)
- [ ] Backup and recovery (RTO/RPO)
- [ ] Multi-AZ for high availability
- [ ] Read replicas for read-heavy workloads

### Operations
- [ ] CloudWatch alarms and dashboards
- [ ] X-Ray tracing
- [ ] Log retention and analysis
- [ ] Cost estimation and tagging

### Terraform Patterns
- [ ] Module structure (reusable components)
- [ ] State management (S3 + DynamoDB locking)
- [ ] Environment separation (workspaces or directories)
- [ ] Variable validation

**Output Template:**
```markdown
# AWS Design: {goal}

## Architecture Diagram
{ASCII or description}

## Components
{List of AWS resources}

## Security Design
{IAM, security groups, encryption}

## Network Design
{VPC, subnets, routing}

## Terraform Structure
{Module organization}

## Cost Estimate
{Monthly cost breakdown}

## Checklist Verification
{Completed checklist items}
```

---

## Domain: Python Code

**Checklist:**

### SOLID Principles
- [ ] **S**ingle Responsibility: Each class/function does one thing
- [ ] **O**pen/Closed: Open for extension, closed for modification
- [ ] **L**iskov Substitution: Subtypes substitutable for base types
- [ ] **I**nterface Segregation: Small, specific interfaces
- [ ] **D**ependency Inversion: Depend on abstractions, not concretions

### Type System
- [ ] Type hints on all public functions
- [ ] Pydantic models for data validation
- [ ] TypedDict for structured dictionaries
- [ ] Generic types where appropriate
- [ ] mypy compatibility

### Error Handling (per CLAUDE.md Principle #8)
- [ ] Workflow nodes: State-based error propagation
- [ ] Utility functions: Raise descriptive exceptions
- [ ] No silent failures (don't return None on error)
- [ ] Explicit error types (custom exceptions)

### Testing
- [ ] Unit test strategy (what to mock)
- [ ] Integration test boundaries
- [ ] Test tier classification (0-4)
- [ ] Property-based testing candidates

### Patterns
- [ ] Repository pattern for data access
- [ ] Factory pattern for object creation
- [ ] Strategy pattern for interchangeable algorithms
- [ ] Decorator pattern for cross-cutting concerns

### Code Organization
- [ ] Module structure (where files go)
- [ ] Import organization
- [ ] Naming conventions (snake_case, PascalCase)
- [ ] Docstring style (Google format)

**Output Template:**
```markdown
# Python Design: {goal}

## Architecture Overview
{High-level structure}

## Class/Module Design
{UML-style class descriptions}

## Type Definitions
{Pydantic models, TypedDicts}

## Error Handling Strategy
{How errors flow}

## Testing Strategy
{Test tiers and boundaries}

## Code Organization
{File structure}

## SOLID Verification
{How design adheres to SOLID}
```

---

## Domain: API Design

**Checklist:**

### Endpoints
- [ ] RESTful resource naming (/users, /reports)
- [ ] HTTP methods (GET, POST, PUT, DELETE, PATCH)
- [ ] URL parameters vs query parameters vs body
- [ ] Pagination strategy (cursor vs offset)
- [ ] Filtering and sorting

### Authentication & Authorization
- [ ] Authentication method (JWT, API key, OAuth)
- [ ] Authorization model (RBAC, ABAC)
- [ ] Token handling (expiry, refresh)
- [ ] Rate limiting strategy

### Request/Response
- [ ] Request validation (Pydantic models)
- [ ] Response format (JSON structure)
- [ ] Error response format (error codes, messages)
- [ ] HTTP status codes (200, 201, 400, 401, 403, 404, 500)

### Versioning
- [ ] Versioning strategy (URL path, header, query param)
- [ ] Backward compatibility
- [ ] Deprecation policy

### Documentation
- [ ] OpenAPI/Swagger spec
- [ ] Example requests/responses
- [ ] Error code documentation

### Performance
- [ ] Caching strategy (ETag, Cache-Control)
- [ ] Compression (gzip)
- [ ] Async operations (for long-running tasks)

**Output Template:**
```markdown
# API Design: {goal}

## Endpoint Overview
{Table of endpoints}

## Authentication
{Auth strategy and flow}

## Endpoint Details

### {Endpoint 1}
- **Method**: GET/POST/PUT/DELETE
- **Path**: /resource/{id}
- **Request**: {Schema}
- **Response**: {Schema}
- **Errors**: {Error codes}

[Repeat for each endpoint]

## Error Handling
{Error response format}

## Rate Limiting
{Limits and headers}

## OpenAPI Spec
{YAML snippet or reference}
```

---

## Domain: Schema Design

**Checklist:**

### Table Design
- [ ] Primary key strategy (auto-increment, UUID, composite)
- [ ] Foreign key relationships
- [ ] Nullable vs NOT NULL decisions
- [ ] Default values

### Data Types (per CLAUDE.md Principle #4)
- [ ] Type compatibility (Python ↔ MySQL)
- [ ] Precision (DECIMAL for money, not FLOAT)
- [ ] Date/time handling (DATETIME with timezone awareness)
- [ ] JSON columns (when appropriate)

### Indexing
- [ ] Primary key index
- [ ] Foreign key indexes
- [ ] Query pattern indexes (covering indexes)
- [ ] Full-text indexes (if needed)

### Normalization
- [ ] 1NF: Atomic values
- [ ] 2NF: No partial dependencies
- [ ] 3NF: No transitive dependencies
- [ ] Denormalization decisions (read performance)

### Migration (per CLAUDE.md Principle #5)
- [ ] Idempotent operations (IF NOT EXISTS)
- [ ] Reconciliation migrations
- [ ] Rollback strategy
- [ ] Data migration (if schema change)

### Performance
- [ ] Query patterns anticipated
- [ ] Read vs write ratio
- [ ] Partitioning strategy (if large tables)
- [ ] Connection pooling

**Output Template:**
```markdown
# Schema Design: {goal}

## Entity Relationship Diagram
{ASCII or description}

## Table Definitions

### {Table 1}
```sql
CREATE TABLE {name} (
  ...
);
```

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| ... | ... | ... | ... |

**Indexes:**
- PRIMARY KEY (id)
- INDEX idx_... (column)

[Repeat for each table]

## Relationships
{Foreign key relationships}

## Migration SQL
{Idempotent migration script}

## Query Patterns
{Expected queries and index usage}
```

---

## Domain: Frontend Design

**Checklist:**

### Component Architecture
- [ ] Component hierarchy
- [ ] Props interface
- [ ] State management (local vs global)
- [ ] Side effects (useEffect patterns)

### State Management
- [ ] Zustand stores (per project conventions)
- [ ] State shape design
- [ ] Selector patterns
- [ ] Subscription optimization

### UI/UX
- [ ] Responsive design breakpoints
- [ ] Accessibility (ARIA, keyboard nav)
- [ ] Loading states
- [ ] Error states
- [ ] Empty states

### Data Fetching
- [ ] API integration
- [ ] Caching strategy
- [ ] Optimistic updates
- [ ] Error handling

### Styling
- [ ] CSS approach (Tailwind, CSS modules)
- [ ] Theme integration
- [ ] Animation patterns

### Testing
- [ ] Component testing strategy
- [ ] Integration test boundaries
- [ ] Visual regression testing

**Output Template:**
```markdown
# Frontend Design: {goal}

## Component Hierarchy
```
App
├── Layout
│   ├── Header
│   └── Content
│       └── {NewComponent}
```

## Component Specification

### {Component Name}
**Props:**
```typescript
interface Props {
  // ...
}
```

**State:**
- Local: {state items}
- Global: {Zustand stores}

**Events:**
- {Event handlers}

## State Management
{Zustand store design}

## Data Flow
{How data flows through components}

## Styling Approach
{CSS strategy}

## Testing Strategy
{Test plan}
```

---

## Output Format

```markdown
# Design: {goal}

**Date**: {YYYY-MM-DD}
**Domain**: {aws | python | api | schema | frontend}

---

## Executive Summary

**What we're designing**: {Brief description}

**Key decisions**:
1. {Decision 1}
2. {Decision 2}
3. {Decision 3}

---

## Design Details

{Domain-specific sections from templates above}

---

## Checklist Verification

{Completed checklist for the domain}

---

## Implementation Notes

**Files to create/modify**:
- {file 1}: {purpose}
- {file 2}: {purpose}

**Dependencies**:
- {dependency 1}
- {dependency 2}

**Testing approach**:
- {test strategy}

---

## Trade-offs Made

| Decision | Alternatives | Why This Choice |
|----------|-------------|-----------------|
| {Decision} | {Options} | {Rationale} |

---

## Next Steps

1. [ ] {Implementation step 1}
2. [ ] {Implementation step 2}
3. [ ] {Implementation step 3}

**Follow-up commands**:
- `/validate "{key assumption}"` - Verify design assumptions
- `EnterPlanMode` - Create implementation plan
```

---

## Examples

### Example 1: AWS Infrastructure Design

```bash
/design "VPC with private subnets for Lambda"
```

**Output:**
```markdown
# Design: VPC with Private Subnets for Lambda

**Domain**: aws

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                │
│  ┌─────────────────┐    ┌─────────────────┐        │
│  │  Public Subnet  │    │  Public Subnet  │        │
│  │   10.0.1.0/24   │    │   10.0.2.0/24   │        │
│  │   (NAT Gateway) │    │   (NAT Gateway) │        │
│  └────────┬────────┘    └────────┬────────┘        │
│           │                      │                  │
│  ┌────────▼────────┐    ┌────────▼────────┐        │
│  │ Private Subnet  │    │ Private Subnet  │        │
│  │   10.0.10.0/24  │    │   10.0.20.0/24  │        │
│  │    (Lambda)     │    │    (Lambda)     │        │
│  └─────────────────┘    └─────────────────┘        │
│                                                     │
│  VPC Endpoints: S3 (Gateway), Secrets Manager      │
└─────────────────────────────────────────────────────┘
```

## Security Design

**Security Groups:**
- Lambda SG: Egress only (to Aurora, NAT, VPC endpoints)
- Aurora SG: Ingress from Lambda SG on 3306

**IAM:**
- Lambda execution role with least privilege
- VPC permissions for ENI management

## Network Design

**VPC Endpoints (to avoid NAT Gateway charges):**
- S3 Gateway Endpoint (free)
- Secrets Manager Interface Endpoint

**NAT Gateway:**
- One per AZ for high availability
- Used only for external API calls (yfinance)

## Checklist Verification

- [x] IAM roles with least privilege
- [x] Security groups (Lambda → Aurora only)
- [x] VPC endpoints for S3 (avoid NAT)
- [x] Multi-AZ subnets
- [x] NAT Gateway for external access
- [x] CIDR non-overlapping
```

---

### Example 2: Python Code Design

```bash
/design python "Repository pattern for Aurora access"
```

**Output:**
```markdown
# Design: Repository Pattern for Aurora Access

**Domain**: python

## Architecture Overview

```
┌─────────────────┐
│   Service Layer │
│   (workflow.py) │
└────────┬────────┘
         │ uses
┌────────▼────────┐
│   Repository    │
│ (data/repos/)   │
└────────┬────────┘
         │ uses
┌────────▼────────┐
│ Database Client │
│ (data/aurora/)  │
└─────────────────┘
```

## Class Design

### Base Repository
```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Abstract base for all repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """Retrieve entity by ID."""
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        """Persist entity."""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Remove entity."""
        pass
```

### Report Repository
```python
class ReportRepository(Repository[Report]):
    """Repository for report entities."""

    def __init__(self, db_client: AuroraClient):
        self._db = db_client

    def get_by_id(self, id: int) -> Optional[Report]:
        result = self._db.execute(
            "SELECT * FROM reports WHERE id = %s", (id,)
        )
        return Report.from_row(result) if result else None
```

## Error Handling Strategy

Per CLAUDE.md Principle #8:
- Repository methods raise `RepositoryError` on failure
- No silent returns of None on error
- Service layer handles exceptions

```python
class RepositoryError(Exception):
    """Base repository exception."""
    pass

class EntityNotFoundError(RepositoryError):
    """Entity not found in database."""
    pass
```

## SOLID Verification

- **S**: Each repository handles one entity type
- **O**: New entities = new repositories, base unchanged
- **L**: All repositories substitutable via base interface
- **I**: Repository interface minimal (get, save, delete)
- **D**: Service layer depends on Repository ABC, not impl
```

---

## Relationship to Other Commands

**Before `/design`:**
- `/x-ray` - Understand existing systems
- `/what-if` - Compare design alternatives
- `/explore` - Divergent option exploration

**After `/design`:**
- `/validate` - Verify design assumptions
- `EnterPlanMode` - Create implementation plan
- `/adapt` - If adapting from external source

**Workflow:**
```bash
# Understand current state
/x-ray "current data access layer"

# Explore options
/explore "repository pattern approaches"

# Compare alternatives
/what-if "repository vs active record pattern"

# Create design
/design python "repository pattern for Aurora"

# Validate assumptions
/validate "Repository pattern reduces coupling"

# Implement
EnterPlanMode
```

---

## Integration with CLAUDE.md Principles

**Principle #1 (Defensive Programming):**
- Design checklists include validation and error handling

**Principle #4 (Type System Integration):**
- Schema domain checklist includes type compatibility

**Principle #8 (Error Handling Duality):**
- Python domain checklist distinguishes workflow vs utility patterns

**Principle #19 (Cross-Boundary Contract Testing):**
- All domains include boundary/interface considerations

---

## See Also

- **Commands:**
  - `/x-ray` - Inspect existing (before design)
  - `/specify` - Quick design sketch (lighter weight)
  - `/what-if` - Compare alternatives
  - `/adapt` - Integrate external techniques

- **Skills:**
  - [research](../skills/research/) - Investigation methodology
  - [code-review](../skills/code-review/) - Design review patterns

- **Principles:**
  - Principle #1: Defensive Programming
  - Principle #4: Type System Integration
  - Principle #8: Error Handling Duality
