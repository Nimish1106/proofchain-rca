# ProofChain RCA — Technical Walkthrough Script (5–10 Minutes)

**Audience:** Engineering Reviewers & Hackathon Technical Judges

---

## 1. Architectural Separation of Concerns
- **Database Layer (`backend/app/models/`)**: PostgreSQL 19 schema managed via Alembic (`migrations/versions/`). Composite foreign keys `(entity_id, investigation_id)` enforce tenant/investigation isolation at the database level — even across SQLite tests (`PRAGMA foreign_keys=ON`).
- **Validation & Guardrail Layer (`backend/app/schemas/` & `app/agents/nodes/validate_rca.py`)**:
  - Groq is called with `strict=True` JSON Schema structured outputs (`app/services/groq_service.py`).
  - Every AI payload is re-validated in Python with Pydantic v2 (`ConfigDict(extra="forbid")`).
  - `validate_rca.py` checks every UUID reference against the bounded context (`build_rca_context`) and enforces evidence rules:
    - `extracted_fact` with `review_status == "pending"` is blocked from `supports`, `contradicts`, and `source_supported` roles.
    - `extracted_fact` with `review_status == "rejected"` cannot be cited anywhere.
    - `WhyStepProposal` enforces at both schema and DB `CHECK` constraint levels that `source_supported` requires `evidence_item_id` while `hypothesis`/`unknown` forbid it.

## 2. Three Independent LangGraph Workflows
1. **Extraction Graph (`app/agents/graph.py`)**: `load_sources → extract_facts → validate_facts → detect_conflicts → persist_facts`. Verifies verbatim quotes & char offsets against page text and computes deterministic SHA-256 `extraction_hash` to avoid duplicates.
2. **RCA Reasoning Graph (`app/agents/rca_graph.py`)**: Pure, DB-free state machine (`generate_hypotheses → analyze_hypotheses → validate_rca`). Python deterministically assigns `H1/H2/H3` keys so the LLM cannot tamper with key mapping. `rca_service.py` commits `RCAAnalysisRun(status="running")` *before* AI execution, flushes hypotheses before dependent records (preventing FK ordering issues), and rolls back all children atomically on error while marking the run `failed` for auditability.
3. **CAPA Graph (`app/agents/capa_graph.py`)**: Two-node pipeline (`generate_capa → stress_test_capa`) where the second LLM pass acts as an adversarial QA reviewer hardening verification methods, effectiveness criteria, and residual risks.

## 3. Targeted AI Copilot Edits (`app/services/copilot_service.py`)
- The Copilot receives full investigation context (fields, evidence, hypotheses, gaps, CAPAs) and returns structured `suggested_edits`.
- Applying edits goes through `POST /api/v1/investigations/{id}/copilot/apply`, which restricts edits to `EDITABLE_INVESTIGATION_FIELDS`, validates dates/decimals, and mutates only the explicitly approved fields.

## 4. Frontend State & Visualization (`frontend/src/`)
- **Redux Toolkit** (`investigationsSlice.ts` + `workspaceSlice.ts`) manages async thunks against `/api/v1` with clean loading/error states.
- **`@xyflow/react`** renders a live causal graph mapping `Investigation → Hypotheses → Linked Evidence (color-coded by supports/contradicts/contextual) → CAPAs`.
- Built cleanly with `tsc -b && vite build` and `oxlint` (0 warnings, 0 errors).

## 5. Verification Coverage
- **122 automated pytest tests** covering schemas, prompts, LangGraph nodes, full graph integration, atomic persistence/rollback, API endpoints, human review gates, CAPA 2-stage workflow, text/email ingestion, and Copilot targeted edits.
- **`alembic check`** confirms zero schema drift against PostgreSQL 19.
