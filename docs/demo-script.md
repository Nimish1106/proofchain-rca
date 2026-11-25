# ProofChain RCA — Product Demo Script (5–8 Minutes)

**Audience:** Judges, Quality Assurance Leads, Manufacturing Engineers  
**Goal:** Demonstrate how ProofChain RCA turns unstructured pharmaceutical deviation evidence into traceable hypotheses, 5-Whys, open evidence gaps, and stress-tested CAPAs — with humans in control at every decision gate.

---

## 0:00 – 0:45 | Problem & Value Proposition
- **Talk track:** In pharmaceutical API manufacturing, deviation and OOS investigations fail audits when root causes are guessed without traceable evidence or when AI hallucinations slip into official QA records.
- **Show:** The **ProofChain RCA Command Center** (`/`), highlighting live API connectivity, investigation KPIs, and clean navigation.

## 0:45 – 2:00 | Investigation Creation & Multi-Source Ingestion
- Click **New Investigation** and create a deviation (e.g., *Reactor R-204 Cooling Temperature Excursion — Atorvastatin Calcium API*).
- Open the two-panel **Investigation Workspace** (`/investigations/:id`).
- Click **Add Source** and show all three ingestion channels:
  1. **PDF Upload** (page-by-page extraction with source offsets).
  2. **Paste Text / Log** (e.g., an operator shift log noting cooling valve V-104 stuck at 20%).
  3. **Ingest Email** (maintenance correspondence noting actuator seal wear).
- Click **View** on a source document to open the **Document Viewer Modal** showing exact page excerpts and original download.

## 2:00 – 3:15 | Fact Extraction & Human Review Gate
- Click **Extract Facts** in the top bar.
- Show extracted facts arriving in `pending` status — never automatically overwriting the official investigation fields.
- Accept one extracted fact via **Accept & Apply Field**, demonstrating how human sign-off updates the Investigation metadata cleanly.
- Reject an irrelevant item or resolve a conflicting candidate in the Conflict Resolution banner.

## 3:15 – 4:45 | Evidence-First RCA & 5-Whys Causal Graph
- Click **Run RCA Analysis**.
- Switch to the **RCA Hypotheses** tab:
  - Point out the yellow governance banner: every AI-generated hypothesis starts as **`proposed`**.
  - Inspect linked evidence cards (`supports` / `contradicts` / `contextual`) and rationales.
  - Change a hypothesis status to `confirmed_by_investigator` with a review note and save.
- Switch to **5-Whys & Graph**:
  - Pan/zoom the **React Flow Causal Graph** showing `Investigation → Hypothesis → Evidence → CAPA`.
  - Edit a 5-Whys step inline, noting the distinction between `source_supported` (evidence-linked), `hypothesis`, and `unknown` answers.

## 4:45 – 5:45 | Evidence Gaps & Stress-Tested CAPAs
- Switch to **Evidence Gaps**: mark an open gap as `addressed` with a resolution note.
- Click **Generate CAPA**, then open the **CAPA** tab:
  - Explain that CAPAs passed a two-stage LangGraph generator + adversarial QA stress-test (adding measurable verification methods, effectiveness criteria, and residual risks).
  - Approve a Corrective Action with a QA review note.

## 5:45 – 6:30 | AI Copilot & Run History Auditability
- Open the **AI Copilot** drawer:
  - Ask `"Update immediate containment to isolate Reactor R-204 and quarantine Batch ATV-2026-041."`
  - Show the proposed field diff card (`current_value → suggested_value`) and click **Apply Proposed Edits** — confirming unrelated fields stay untouched.
- Briefly show **Runs** tab: immutable `RCAAnalysisRun` audit trail with model ID and SHA-256 `input_fingerprint`.
