# ProofChain RCA — System Architecture

## 1. High-Level System Architecture

```mermaid
flowchart LR
    UI["React 19 + Redux Toolkit UI<br/>(React Flow Graph & Copilot)"] -->|HTTP / JSON + FormData| API["FastAPI /api/v1"]
    API --> Services["Domain Services<br/>(Document, Extraction, RCA, CAPA, Copilot)"]
    Services --> Graphs["LangGraph Pipelines"]
    Graphs -->|Strict JSON Schema| Groq["Groq LLM API<br/>(openai/gpt-oss-20b)"]
    Services --> DB["PostgreSQL 19<br/>(Composite FK Isolation)"]
    Services --> Files["Private Local File Store<br/>(var/uploads)"]
```

## 2. Multi-Pipeline LangGraph Orchestration

### A. Source-Grounded Fact Extraction (`app/agents/graph.py`)
```mermaid
flowchart LR
    LS["load_sources"] --> EF["extract_facts"]
    EF --> VF["validate_facts<br/>(quote & offset check)"]
    VF --> DC["detect_conflicts<br/>(flag differing candidates)"]
    DC --> PF["persist_facts<br/>(status = pending)"]
```

### B. Evidence-First RCA Reasoning (`app/agents/rca_graph.py`)
```mermaid
flowchart LR
    CTX["build_rca_context<br/>(SHA-256 fingerprint + bounds)"] --> GH["generate_hypotheses<br/>(max 3, assign H1..H3)"]
    GH --> AH["analyze_hypotheses<br/>(5-Whys + evidence gaps)"]
    AH --> VR["validate_rca<br/>(reject pending/rejected misuse)"]
    VR --> DB["Atomic Persist<br/>(all hypotheses = proposed)"]
```

### C. Two-Stage CAPA Generation & Stress Testing (`app/agents/capa_graph.py`)
```mermaid
flowchart LR
    LOAD["Load Non-Rejected Hypotheses<br/>+ Evidence + 5-Whys"] --> GEN["generate_capa<br/>(Corrective & Preventive)"]
    GEN --> ST["stress_test_capa<br/>(Verification & Residual Risk Audit)"]
    ST --> SAVE["Persist CAPARecommendation<br/>(status = proposed)"]
```

## 3. Database Isolation & Referential Integrity

Every child table (`source_documents`, `evidence_items`, `rca_analysis_runs`, `rca_hypotheses`, `hypothesis_evidence`, `why_steps`, `evidence_gaps`, `capa_recommendations`) enforces **same-investigation scoping** via composite foreign keys `(entity_id, investigation_id)` and SQLite/PostgreSQL `CHECK` constraints:

- `evidence_items.review_status`: `pending | accepted | rejected`
- `rca_hypotheses.status`: `proposed | under_review | supported_by_records | contradicted | rejected | confirmed_by_investigator`
- `why_steps.answer_basis`: `source_supported` (requires `evidence_item_id`) vs `hypothesis | unknown` (`evidence_item_id IS NULL`)
- `capa_recommendations.status`: `proposed | approved | in_progress | completed | rejected`
