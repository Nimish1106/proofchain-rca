# ProofChain RCA — Submission & Verification Checklist

## Backend Capabilities
- [x] Investigation CRUD with strict Pydantic validation (`PATCH` preserves unmodified fields)
- [x] PDF upload, private storage, and PyMuPDF page-by-page extraction
- [x] Plain-text log ingestion (`POST /api/v1/investigations/{id}/ingest-text`)
- [x] Email ingestion (`POST /api/v1/investigations/{id}/ingest-email`)
- [x] Document inline content preview (`GET /api/v1/investigations/{id}/documents/{doc_id}/content`) & download
- [x] LangGraph source-grounded fact extraction with verbatim quote validation & conflict detection
- [x] Bounded RCA context builder with SHA-256 `input_fingerprint`
- [x] LangGraph RCA reasoning (`generate_hypotheses → analyze_hypotheses → validate_rca`)
- [x] Pending/rejected fact guardrails + all hypotheses initialized as `proposed`
- [x] Versioned `RCAAnalysisRun` audit history with atomic rollback on failure
- [x] Human review workflow endpoints (evidence accept/reject + optional apply-to-investigation, hypothesis status/note, 5-Whys editing, gap resolution/waiver/reopen)
- [x] Two-stage CAPA LangGraph engine (`generate_capa → stress_test_capa`) + persistence & status workflow
- [x] AI Copilot Q&A + targeted field-edit proposals & safe application (`POST /copilot/apply`)

## Frontend Capabilities
- [x] Dashboard with API health badge, KPIs, and quick investigation creation
- [x] Searchable & filterable Investigations list
- [x] Two-panel Investigation Workspace with real API integration throughout
- [x] Multi-source ingestion modal (PDF, Text, Email) + Document Viewer modal
- [x] Evidence review & conflict resolution UI
- [x] Hypothesis review cards, inline 5-Whys editor, and Evidence Gaps management
- [x] Interactive `@xyflow/react` causal graph (`Investigation → Hypotheses → Evidence → CAPAs`)
- [x] CAPA management panel + Run History audit inspector
- [x] Toggleable AI Copilot drawer with one-click targeted edit application

## Automated Verification
- [x] `pytest -v tests` — **122 passed**
- [x] `alembic check` — **No new upgrade operations detected**
- [x] `npm run build` (`tsc -b && vite build`) — **Succeeded with 0 errors**
- [x] `npm run lint` (`oxlint`) — **0 warnings, 0 errors**
