import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiClient } from '../api/client';
import type {
  CAPARecommendation,
  CopilotFieldEdit,
  CopilotResponse,
  DocumentContentResponse,
  EvidenceItem,
  ExtractionRunResponse,
  HypothesisStatus,
  RCARunDetail,
  RCARunSummary,
  SourceDocument,
} from '../types/api';

export interface CopilotTurn {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  suggestedEdits?: CopilotFieldEdit[];
  warnings?: string[];
  applied?: boolean;
}

interface WorkspaceState {
  investigationId: string | null;
  documents: SourceDocument[];
  documentPreview: DocumentContentResponse | null;
  evidence: EvidenceItem[];
  lastExtraction: ExtractionRunResponse | null;
  rcaRuns: RCARunSummary[];
  activeRcaRun: RCARunDetail | null;
  capas: CAPARecommendation[];
  copilotHistory: CopilotTurn[];
  loadingWorkspace: boolean;
  runningExtraction: boolean;
  runningRca: boolean;
  runningCapa: boolean;
  runningCopilot: boolean;
  ingesting: boolean;
  error: string | null;
  notice: string | null;
}

const initialState: WorkspaceState = {
  investigationId: null,
  documents: [],
  documentPreview: null,
  evidence: [],
  lastExtraction: null,
  rcaRuns: [],
  activeRcaRun: null,
  capas: [],
  copilotHistory: [],
  loadingWorkspace: false,
  runningExtraction: false,
  runningRca: false,
  runningCapa: false,
  runningCopilot: false,
  ingesting: false,
  error: null,
  notice: null,
};

export const loadWorkspaceData = createAsyncThunk(
  'workspace/loadAll',
  async (investigationId: string) => {
    const [docsRes, evRes, rcaRes, capaRes] = await Promise.all([
      apiClient.listDocuments(investigationId),
      apiClient.listEvidence(investigationId),
      apiClient.listRcaRuns(investigationId),
      apiClient.listCapa(investigationId),
    ]);

    const latestCompleted = rcaRes.items.find((r) => r.status === 'completed');
    const activeRun = latestCompleted
      ? await apiClient.getRcaRun(investigationId, latestCompleted.id)
      : null;

    return {
      investigationId,
      documents: docsRes.items,
      evidence: evRes.items,
      rcaRuns: rcaRes.items,
      activeRcaRun: activeRun,
      capas: capaRes.items,
    };
  },
);

export const uploadPdfDocument = createAsyncThunk(
  'workspace/uploadPdf',
  async ({ investigationId, file }: { investigationId: string; file: File }) => {
    const res = await apiClient.uploadPdf(investigationId, file);
    const evRes = await apiClient.listEvidence(investigationId);
    return { upload: res, evidence: evRes.items };
  },
);

export const ingestTextSource = createAsyncThunk(
  'workspace/ingestText',
  async ({
    investigationId,
    title,
    content,
  }: {
    investigationId: string;
    title: string;
    content: string;
  }) => {
    const res = await apiClient.ingestText(investigationId, { title, content });
    const evRes = await apiClient.listEvidence(investigationId);
    return { upload: res, evidence: evRes.items };
  },
);

export const ingestEmailSource = createAsyncThunk(
  'workspace/ingestEmail',
  async ({
    investigationId,
    subject,
    sender,
    date,
    body,
  }: {
    investigationId: string;
    subject: string;
    sender: string;
    date?: string;
    body: string;
  }) => {
    const res = await apiClient.ingestEmail(investigationId, {
      subject,
      sender,
      date,
      body,
    });
    const evRes = await apiClient.listEvidence(investigationId);
    return { upload: res, evidence: evRes.items };
  },
);

export const fetchDocumentPreview = createAsyncThunk(
  'workspace/docPreview',
  async ({ investigationId, documentId }: { investigationId: string; documentId: string }) =>
    apiClient.getDocumentContent(investigationId, documentId),
);

export const runFactExtraction = createAsyncThunk(
  'workspace/extractFacts',
  async (investigationId: string) => {
    const extraction = await apiClient.extractFacts(investigationId);
    const evRes = await apiClient.listEvidence(investigationId);
    return { extraction, evidence: evRes.items };
  },
);

export const reviewEvidenceItem = createAsyncThunk(
  'workspace/reviewEvidence',
  async ({
    investigationId,
    evidenceId,
    review_status,
    apply_to_investigation,
  }: {
    investigationId: string;
    evidenceId: string;
    review_status: 'pending' | 'accepted' | 'rejected';
    apply_to_investigation?: boolean;
  }) =>
    apiClient.reviewEvidence(investigationId, evidenceId, {
      review_status,
      apply_to_investigation,
    }),
);

export const runRCAAnalysis = createAsyncThunk(
  'workspace/runRca',
  async (investigationId: string) => {
    const detail = await apiClient.runRca(investigationId);
    const runsRes = await apiClient.listRcaRuns(investigationId);
    return { detail, runs: runsRes.items };
  },
);

export const selectRCARun = createAsyncThunk(
  'workspace/selectRcaRun',
  async ({ investigationId, runId }: { investigationId: string; runId: string }) =>
    apiClient.getRcaRun(investigationId, runId),
);

export const reviewHypothesisItem = createAsyncThunk(
  'workspace/reviewHypothesis',
  async ({
    investigationId,
    hypothesisId,
    status,
    review_note,
  }: {
    investigationId: string;
    hypothesisId: string;
    status: HypothesisStatus;
    review_note?: string;
  }) =>
    apiClient.reviewHypothesis(investigationId, hypothesisId, {
      status,
      review_note,
    }),
);

export const editWhyStepItem = createAsyncThunk(
  'workspace/editWhyStep',
  async ({
    investigationId,
    stepId,
    question,
    answer,
  }: {
    investigationId: string;
    stepId: string;
    question?: string;
    answer?: string;
  }) => apiClient.editWhyStep(investigationId, stepId, { question, answer }),
);

export const resolveGapItem = createAsyncThunk(
  'workspace/resolveGap',
  async ({
    investigationId,
    gapId,
    status,
    resolution_note,
  }: {
    investigationId: string;
    gapId: string;
    status: 'open' | 'addressed' | 'waived';
    resolution_note?: string;
  }) =>
    apiClient.resolveEvidenceGap(investigationId, gapId, {
      status,
      resolution_note,
    }),
);

export const generateCapaItems = createAsyncThunk(
  'workspace/generateCapa',
  async (investigationId: string) => {
    await apiClient.generateCapa(investigationId);
    const list = await apiClient.listCapa(investigationId);
    return list.items;
  },
);

export const updateCapaItemStatus = createAsyncThunk(
  'workspace/updateCapa',
  async ({
    investigationId,
    capaId,
    status,
    review_note,
  }: {
    investigationId: string;
    capaId: string;
    status: string;
    review_note?: string;
  }) =>
    apiClient.updateCapaStatus(investigationId, capaId, {
      status,
      review_note,
    }),
);

export const askCopilotQuestion = createAsyncThunk(
  'workspace/askCopilot',
  async ({
    investigationId,
    message,
    context_type,
  }: {
    investigationId: string;
    message: string;
    context_type?: string;
  }): Promise<{ prompt: string; response: CopilotResponse }> => {
    const response = await apiClient.askCopilot(investigationId, {
      message,
      context_type,
    });
    return { prompt: message, response };
  },
);

export const applyCopilotSuggestedEdits = createAsyncThunk(
  'workspace/applyCopilotEdits',
  async ({
    investigationId,
    turnId,
    edits,
  }: {
    investigationId: string;
    turnId: string;
    edits: CopilotFieldEdit[];
  }) => {
    const investigation = await apiClient.applyCopilotEdits(investigationId, edits);
    return { turnId, investigation };
  },
);

const workspaceSlice = createSlice({
  name: 'workspace',
  initialState,
  reducers: {
    clearWorkspaceMessages(state) {
      state.error = null;
      state.notice = null;
    },
    closeDocumentPreview(state) {
      state.documentPreview = null;
    },
    clearCopilotChat(state) {
      state.copilotHistory = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadWorkspaceData.pending, (state, action) => {
        state.loadingWorkspace = true;
        state.error = null;
        if (state.investigationId !== action.meta.arg) {
          state.copilotHistory = [];
          state.lastExtraction = null;
          state.documentPreview = null;
        }
        state.investigationId = action.meta.arg;
      })
      .addCase(loadWorkspaceData.fulfilled, (state, action) => {
        state.loadingWorkspace = false;
        state.documents = action.payload.documents;
        state.evidence = action.payload.evidence;
        state.rcaRuns = action.payload.rcaRuns;
        state.activeRcaRun = action.payload.activeRcaRun;
        state.capas = action.payload.capas;
      })
      .addCase(loadWorkspaceData.rejected, (state, action) => {
        state.loadingWorkspace = false;
        state.error = action.error.message ?? 'Failed to load workspace';
      })

      // Ingestion
      .addCase(uploadPdfDocument.pending, (state) => {
        state.ingesting = true;
        state.error = null;
      })
      .addCase(uploadPdfDocument.fulfilled, (state, action) => {
        state.ingesting = false;
        state.documents.unshift(action.payload.upload.document);
        state.evidence = action.payload.evidence;
        state.notice = `Uploaded ${action.payload.upload.document.original_filename} (${action.payload.upload.evidence_items_created} source excerpts).`;
      })
      .addCase(uploadPdfDocument.rejected, (state, action) => {
        state.ingesting = false;
        state.error = action.error.message ?? 'PDF upload failed';
      })
      .addCase(ingestTextSource.pending, (state) => {
        state.ingesting = true;
        state.error = null;
      })
      .addCase(ingestTextSource.fulfilled, (state, action) => {
        state.ingesting = false;
        state.documents.unshift(action.payload.upload.document);
        state.evidence = action.payload.evidence;
        state.notice = `Ingested text note "${action.payload.upload.document.original_filename}".`;
      })
      .addCase(ingestTextSource.rejected, (state, action) => {
        state.ingesting = false;
        state.error = action.error.message ?? 'Text ingestion failed';
      })
      .addCase(ingestEmailSource.pending, (state) => {
        state.ingesting = true;
        state.error = null;
      })
      .addCase(ingestEmailSource.fulfilled, (state, action) => {
        state.ingesting = false;
        state.documents.unshift(action.payload.upload.document);
        state.evidence = action.payload.evidence;
        state.notice = `Ingested email "${action.payload.upload.document.original_filename}".`;
      })
      .addCase(ingestEmailSource.rejected, (state, action) => {
        state.ingesting = false;
        state.error = action.error.message ?? 'Email ingestion failed';
      })
      .addCase(fetchDocumentPreview.fulfilled, (state, action) => {
        state.documentPreview = action.payload;
      })
      .addCase(fetchDocumentPreview.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to load document preview';
      })

      // Extraction & Evidence Review
      .addCase(runFactExtraction.pending, (state) => {
        state.runningExtraction = true;
        state.error = null;
      })
      .addCase(runFactExtraction.fulfilled, (state, action) => {
        state.runningExtraction = false;
        state.lastExtraction = action.payload.extraction;
        state.evidence = action.payload.evidence;
        state.notice = `Fact extraction finished: ${action.payload.extraction.new_facts_count} new facts awaiting human review.`;
      })
      .addCase(runFactExtraction.rejected, (state, action) => {
        state.runningExtraction = false;
        state.error = action.error.message ?? 'Fact extraction failed';
      })
      .addCase(reviewEvidenceItem.fulfilled, (state, action) => {
        const idx = state.evidence.findIndex((e) => e.id === action.payload.id);
        if (idx >= 0) state.evidence[idx] = action.payload;
        state.notice = `Evidence marked as ${action.payload.review_status}.`;
      })
      .addCase(reviewEvidenceItem.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to review evidence';
      })

      // RCA
      .addCase(runRCAAnalysis.pending, (state) => {
        state.runningRca = true;
        state.error = null;
      })
      .addCase(runRCAAnalysis.fulfilled, (state, action) => {
        state.runningRca = false;
        state.activeRcaRun = action.payload.detail;
        state.rcaRuns = action.payload.runs;
        state.notice = `RCA analysis completed (${action.payload.detail.hypotheses.length} proposed hypotheses).`;
      })
      .addCase(runRCAAnalysis.rejected, (state, action) => {
        state.runningRca = false;
        state.error = action.error.message ?? 'RCA execution failed';
      })
      .addCase(selectRCARun.fulfilled, (state, action) => {
        state.activeRcaRun = action.payload;
      })
      .addCase(reviewHypothesisItem.fulfilled, (state, action) => {
        if (!state.activeRcaRun) return;
        const hyp = state.activeRcaRun.hypotheses.find((h) => h.id === action.payload.id);
        if (hyp) {
          hyp.status = action.payload.status;
          hyp.review_note = action.payload.review_note;
          hyp.reviewed_at = action.payload.reviewed_at;
        }
        state.notice = `Hypothesis status updated to "${action.payload.status}".`;
      })
      .addCase(reviewHypothesisItem.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to update hypothesis';
      })
      .addCase(editWhyStepItem.fulfilled, (state, action) => {
        if (!state.activeRcaRun) return;
        for (const hyp of state.activeRcaRun.hypotheses) {
          const step = hyp.why_steps.find((s) => s.id === action.payload.id);
          if (step) {
            step.question = action.payload.question;
            step.answer = action.payload.answer;
            step.updated_at = action.payload.updated_at;
          }
        }
        state.notice = '5-Whys step updated.';
      })
      .addCase(editWhyStepItem.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to edit Why step';
      })
      .addCase(resolveGapItem.fulfilled, (state, action) => {
        if (!state.activeRcaRun) return;
        const gGap = state.activeRcaRun.global_gaps.find((g) => g.id === action.payload.id);
        if (gGap) Object.assign(gGap, action.payload);
        for (const hyp of state.activeRcaRun.hypotheses) {
          const hGap = hyp.evidence_gaps.find((g) => g.id === action.payload.id);
          if (hGap) Object.assign(hGap, action.payload);
        }
        state.notice = `Evidence gap marked "${action.payload.status}".`;
      })
      .addCase(resolveGapItem.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to update evidence gap';
      })

      // CAPA
      .addCase(generateCapaItems.pending, (state) => {
        state.runningCapa = true;
        state.error = null;
      })
      .addCase(generateCapaItems.fulfilled, (state, action) => {
        state.runningCapa = false;
        state.capas = action.payload;
        state.notice = 'Stress-tested CAPA recommendations generated.';
      })
      .addCase(generateCapaItems.rejected, (state, action) => {
        state.runningCapa = false;
        state.error = action.error.message ?? 'CAPA generation failed';
      })
      .addCase(updateCapaItemStatus.fulfilled, (state, action) => {
        const idx = state.capas.findIndex((c) => c.id === action.payload.id);
        if (idx >= 0) state.capas[idx] = action.payload;
        state.notice = `CAPA marked "${action.payload.status}".`;
      })
      .addCase(updateCapaItemStatus.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to update CAPA';
      })

      // Copilot
      .addCase(askCopilotQuestion.pending, (state, action) => {
        state.runningCopilot = true;
        state.error = null;
        state.copilotHistory.push({
          id: `u-${Date.now()}`,
          role: 'user',
          text: action.meta.arg.message,
        });
      })
      .addCase(askCopilotQuestion.fulfilled, (state, action) => {
        state.runningCopilot = false;
        state.copilotHistory.push({
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: action.payload.response.message,
          suggestedEdits: action.payload.response.suggested_edits,
          warnings: action.payload.response.warnings,
        });
      })
      .addCase(askCopilotQuestion.rejected, (state, action) => {
        state.runningCopilot = false;
        state.copilotHistory.push({
          id: `err-${Date.now()}`,
          role: 'assistant',
          text: `Error: ${action.error.message ?? 'Copilot request failed.'}`,
        });
      })
      .addCase(applyCopilotSuggestedEdits.fulfilled, (state, action) => {
        const turn = state.copilotHistory.find((t) => t.id === action.payload.turnId);
        if (turn) turn.applied = true;
        state.notice = 'Targeted Copilot edit applied to investigation.';
      })
      .addCase(applyCopilotSuggestedEdits.rejected, (state, action) => {
        state.error = action.error.message ?? 'Failed to apply Copilot edit';
      });
  },
});

export const {
  clearWorkspaceMessages,
  closeDocumentPreview,
  clearCopilotChat,
} = workspaceSlice.actions;
export default workspaceSlice.reducer;
