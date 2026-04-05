---
name: architect-pro
description: This skill should be used when the user asks to "design the architecture", "plan the system", "create a technical design", "draw a diagram", "generate a C4 diagram", "create a Mermaid flowchart", "architect this feature", or "plan before we build". Generates a diagram BEFORE any implementation begins and requires explicit user confirmation to proceed.
version: 0.1.0
---

# Architect Pro

Generate a C4 or Mermaid diagram before any implementation begins. Do not write implementation code until the user confirms the architecture is correct.

## Core Rule

The diagram is the deliverable of this skill. Implementation is a separate subsequent step. After producing the diagram, ask for confirmation and stop.

## Diagram Selection

| Scenario | Diagram Type |
|---|---|
| New system or major feature | C4 Context + Container |
| Data flow or process | Mermaid flowchart (`graph LR`) |
| Sequence of interactions between components | Mermaid sequence diagram |
| Database schema | Mermaid entity-relationship diagram |
| State machine or lifecycle | Mermaid state diagram |
| Zooming into an existing system | C4 Component diagram |

When in doubt between flowchart and sequence diagram: if time/order matters, use sequence; if topology matters, use flowchart.

## C4 Templates

### Context Level (start here for new systems)

```mermaid
C4Context
  title System Context — <Feature Name>

  Person(user, "User", "<who uses this>")
  System(sys, "<System Name>", "<what it does>")
  System_Ext(ext, "<External System>", "<third-party service>")

  Rel(user, sys, "Uses", "HTTPS")
  Rel(sys, ext, "Calls", "REST API")
```

### Container Level (zoom in to services)

```mermaid
C4Container
  title Container Diagram — <Feature Name>

  Container(web, "Web App", "React", "User interface")
  Container(api, "API Server", "Node/Express", "Business logic")
  ContainerDb(db, "Database", "PostgreSQL", "Persistent storage")
  Container_Ext(cache, "Cache", "Redis", "Session and result caching")

  Rel(web, api, "API calls", "HTTPS/JSON")
  Rel(api, db, "Reads/writes", "SQL")
  Rel(api, cache, "Caches", "Redis protocol")
```

## Mermaid Templates

### Flowchart

```mermaid
graph LR
    A[User Request] --> B{Auth Check}
    B -->|Authenticated| C[Process Request]
    B -->|Unauthenticated| D[Return 401]
    C --> E[Fetch Data]
    E --> F{Cache Hit?}
    F -->|Yes| G[Return Cached]
    F -->|No| H[Query DB]
    H --> I[Cache Result]
    I --> G
    G --> J[Return Response]
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant DB as Database
    participant C as Cache

    U->>A: POST /resource
    A->>C: Check cache
    C-->>A: Miss
    A->>DB: INSERT
    DB-->>A: Row ID
    A->>C: Invalidate key
    A-->>U: 201 Created
```

### Entity-Relationship

```mermaid
erDiagram
    USER {
        uuid id PK
        string email
        timestamp created_at
    }
    ORDER {
        uuid id PK
        uuid user_id FK
        decimal amount
        string status
    }
    USER ||--o{ ORDER : places
```

## Workflow

1. If the scope is ambiguous, ask one focused clarifying question before drawing
2. Select the appropriate diagram type
3. Generate the diagram
4. Add a written summary beneath it:
   - Key design decisions made and why
   - Assumptions encoded in the diagram
   - Alternatives considered and why they were rejected (one sentence each)
5. Ask: "Does this architecture look correct? Any changes before we start implementation?"
6. Wait for explicit confirmation — do not proceed to implementation on the same turn

## Diagram Quality Standards

- Label every external system or service with its communication protocol (REST, gRPC, WebSocket, SQL, etc.)
- Label every data store with its technology (PostgreSQL, Redis, S3, etc.)
- Show both the happy path and at least one failure or error path
- Verify the diagram renders correctly before presenting (valid Mermaid syntax)
