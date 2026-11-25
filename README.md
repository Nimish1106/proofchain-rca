# ProofChain RCA

**Evidence-First AI Root Cause Analysis & CAPA Engineering for Pharmaceutical API Manufacturing**

> **Disclaimer:** ProofChain RCA is a hackathon prototype built to demonstrate evidence-first, human-in-the-loop AI workflows for quality deviation investigations. It is not validated for regulated GxP production use.

---

## Core Design Principles

1. **Evidence-First Traceability:** Source documents (PDFs, pasted operator logs, emails) are stored as immutable `source_excerpt` records with document/page/character offsets.
2. **Human-in-the-Loop Control:** AI-extracted facts remain `pending` until an investigator accepts or rejects them. AI-generated RCA hypotheses always start as `proposed` and can never self-confirm.
3. **Strict Grounding Guardrails:** Pending extracted facts cannot support or contradict hypotheses or serve as `source_supported` 5-Whys answers; rejected facts cannot be cited at all.
4. **Versioned Auditability:** Every RCA run creates a `RCAAnalysisRun` snapshot with model identity, SHA-256 `input_fingerprint`, status, and failure error codes.
5. **Adversarial CAPA Stress-Testing:** Proposed Corrective and Preventive Actions go through a two-stage LangGraph workflow (generation followed by adversarial QA critique for measurability and residual risk).

---

## Technology Stack

- **Frontend:** React 19, TypeScript, Redux Toolkit, React Router, `@xyflow/react` (React Flow), `lucide-react`, Vite 8
- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PyMuPDF (`pymupdf`)
- **AI Orchestration:** LangGraph + Groq (`openai/gpt-oss-20b` with strict JSON Schema structured outputs)
- **Database:** PostgreSQL 19 (production/dev) and SQLite in-memory with `PRAGMA foreign_keys=ON` (unit/API tests)

---

## Screenshots 
<img width="1896" height="835" alt="image" src="https://github.com/user-attachments/assets/65720b53-1a1a-43c6-a89b-c2f4ea248a9b" />
<img width="1758" height="773" alt="image" src="https://github.com/user-attachments/assets/b45494f4-908c-4c8d-8f33-cf83027a1e19" />


## Project Structure

```text
proofchain-rca/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph workflows (extraction, RCA, CAPA) & prompts
│   │   ├── api/routes/      # FastAPI v1 routes (investigations, documents, evidence, analysis, rca, review, capa, copilot, ingestion)
│   │   ├── core/            # Settings & logging
│   │   ├── database/        # SQLAlchemy base & session
│   │   ├── models/          # ORM models with composite same-investigation FKs
│   │   ├── schemas/         # Pydantic contracts & Groq strict JSON schemas
│   │   └── services/        # Business logic & transaction boundaries
│   ├── migrations/          # Alembic migrations
│   └── tests/               # Pytest suite (122 tests)
├── frontend/
│   ├── src/
│   │   ├── api/             # Centralized typed fetch client
│   │   ├── components/      # EvidenceGraph (React Flow), CopilotPanel, Ingestion/Viewer modals, StatusBadge
│   │   ├── pages/           # Dashboard, InvestigationsList, InvestigationWorkspace
│   │   ├── store/           # Redux Toolkit slices & async thunks
│   │   └── types/           # TypeScript API contracts
├── docs/                    # Architecture, demo script, technical walkthrough, submission checklist
└── .env.example             # Configuration template
```

---

## Setup & Running Locally

### 1. Environment Variables
Copy `.env.example` to `.env` in the repository root and configure:
- `DATABASE_URL` (PostgreSQL connection string)
- `GROQ_API_KEY` and `GROQ_MODEL` (e.g., `openai/gpt-oss-20b`)

### 2. Backend Setup
```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Backend API runs at `http://127.0.0.1:8000` (OpenAPI docs at `/docs`, health at `/api/v1/health`).

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`. Optionally set `VITE_API_BASE_URL` in `frontend/.env`.

### 4. Running Tests & Verification
```powershell
# Backend tests (122 tests, isolated SQLite)
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v

# Migration schema drift check
.\.venv\Scripts\alembic.exe check

# Frontend typecheck, production build & lint
cd ..\frontend
npm run build
npm run lint
```

---

## Key API Endpoints (`/api/v1`)

| Area | Endpoints |
| :--- | :--- |
| Health | `GET /health` |
| Investigations | `POST /investigations`, `GET /investigations`, `GET /investigations/{id}`, `PATCH /investigations/{id}` |
| Sources & Ingestion | `POST /investigations/{id}/documents`, `POST /investigations/{id}/ingest-text`, `POST /investigations/{id}/ingest-email`, `GET /investigations/{id}/documents`, `GET /investigations/{id}/documents/{doc_id}/content`, `GET /investigations/{id}/documents/{doc_id}/download` |
| Evidence & Extraction | `GET /investigations/{id}/evidence`, `POST /investigations/{id}/extract-facts`, `PATCH /investigations/{id}/evidence/{ev_id}` |
| RCA Analysis | `POST /investigations/{id}/rca`, `GET /investigations/{id}/rca`, `GET /investigations/{id}/rca/{run_id}` |
| Human Review | `PATCH /investigations/{id}/hypotheses/{hyp_id}`, `PATCH /investigations/{id}/why-steps/{step_id}`, `PATCH /investigations/{id}/evidence-gaps/{gap_id}` |
| CAPA | `POST /investigations/{id}/capa`, `GET /investigations/{id}/capa`, `PATCH /investigations/{id}/capa/{capa_id}` |
| AI Copilot | `POST /investigations/{id}/copilot`, `POST /investigations/{id}/copilot/apply` |

---

## Documentation Index

- [Architecture & Workflows](docs/architecture.md)
- [Product Demo Script (5-8 min)](docs/demo-script.md)
- [Technical Walkthrough Script (5-10 min)](docs/technical-walkthrough.md)
- [Submission Checklist](docs/submission-checklist.md)
