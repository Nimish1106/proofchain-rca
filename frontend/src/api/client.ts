import type {
  CAPARecommendation,
  CopilotFieldEdit,
  CopilotResponse,
  DocumentContentResponse,
  DocumentUploadResponse,
  EvidenceGap,
  EvidenceItem,
  ExtractionRunResponse,
  HypothesisDetail,
  HypothesisStatus,
  Investigation,
  InvestigationCreatePayload,
  InvestigationListResponse,
  InvestigationUpdatePayload,
  RCARunDetail,
  RCARunSummary,
  SourceDocument,
  WhyStep,
} from '../types/api';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
).replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === 'string') {
        detail = payload.detail;
      } else if (Array.isArray(payload?.detail)) {
        detail = payload.detail
          .map((item: { msg?: string }) => item.msg || JSON.stringify(item))
          .join('; ');
      }
    } catch {
      // ignore non-JSON error body
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  getHealth: () => request<{ status: string; service: string }>('/health'),

  // Investigations
  listInvestigations: (limit = 50, offset = 0) =>
    request<InvestigationListResponse>(`/investigations?limit=${limit}&offset=${offset}`),

  getInvestigation: (id: string) =>
    request<Investigation>(`/investigations/${id}`),

  createInvestigation: (payload: InvestigationCreatePayload) =>
    request<Investigation>('/investigations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateInvestigation: (id: string, payload: InvestigationUpdatePayload) =>
    request<Investigation>(`/investigations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  // Documents & Ingestion
  listDocuments: (investigationId: string) =>
    request<{ items: SourceDocument[]; total: number }>(
      `/investigations/${investigationId}/documents?limit=100`,
    ),

  uploadPdf: (investigationId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<DocumentUploadResponse>(
      `/investigations/${investigationId}/documents`,
      { method: 'POST', body: form },
    );
  },

  ingestText: (investigationId: string, payload: { title: string; content: string }) =>
    request<DocumentUploadResponse>(`/investigations/${investigationId}/ingest-text`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  ingestEmail: (
    investigationId: string,
    payload: { subject: string; sender: string; date?: string; body: string },
  ) =>
    request<DocumentUploadResponse>(`/investigations/${investigationId}/ingest-email`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getDocumentContent: (investigationId: string, documentId: string) =>
    request<DocumentContentResponse>(
      `/investigations/${investigationId}/documents/${documentId}/content`,
    ),

  getDocumentDownloadUrl: (investigationId: string, documentId: string) =>
    `${API_BASE}/investigations/${investigationId}/documents/${documentId}/download`,

  // Evidence & Extraction
  listEvidence: (investigationId: string, documentId?: string) => {
    const query = documentId ? `&document_id=${documentId}` : '';
    return request<{ items: EvidenceItem[]; total: number }>(
      `/investigations/${investigationId}/evidence?limit=100${query}`,
    );
  },

  extractFacts: (investigationId: string) =>
    request<ExtractionRunResponse>(`/investigations/${investigationId}/extract-facts`, {
      method: 'POST',
    }),

  reviewEvidence: (
    investigationId: string,
    evidenceId: string,
    payload: {
      review_status: 'pending' | 'accepted' | 'rejected';
      review_note?: string;
      apply_to_investigation?: boolean;
    },
  ) =>
    request<EvidenceItem>(`/investigations/${investigationId}/evidence/${evidenceId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  // RCA
  runRca: (investigationId: string) =>
    request<RCARunDetail>(`/investigations/${investigationId}/rca`, {
      method: 'POST',
    }),

  listRcaRuns: (investigationId: string) =>
    request<{ items: RCARunSummary[]; total: number }>(
      `/investigations/${investigationId}/rca`,
    ),

  getRcaRun: (investigationId: string, runId: string) =>
    request<RCARunDetail>(`/investigations/${investigationId}/rca/${runId}`),

  reviewHypothesis: (
    investigationId: string,
    hypothesisId: string,
    payload: { status: HypothesisStatus; review_note?: string },
  ) =>
    request<HypothesisDetail>(
      `/investigations/${investigationId}/hypotheses/${hypothesisId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
    ),

  editWhyStep: (
    investigationId: string,
    stepId: string,
    payload: { question?: string; answer?: string },
  ) =>
    request<WhyStep>(`/investigations/${investigationId}/why-steps/${stepId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  resolveEvidenceGap: (
    investigationId: string,
    gapId: string,
    payload: { status: 'open' | 'addressed' | 'waived'; resolution_note?: string },
  ) =>
    request<EvidenceGap>(
      `/investigations/${investigationId}/evidence-gaps/${gapId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
    ),

  // CAPA
  listCapa: (investigationId: string) =>
    request<{ items: CAPARecommendation[]; total: number }>(
      `/investigations/${investigationId}/capa`,
    ),

  generateCapa: (investigationId: string) =>
    request<{ items: CAPARecommendation[]; total: number }>(
      `/investigations/${investigationId}/capa`,
      { method: 'POST' },
    ),

  updateCapaStatus: (
    investigationId: string,
    capaId: string,
    payload: { status: string; review_note?: string },
  ) =>
    request<CAPARecommendation>(`/investigations/${investigationId}/capa/${capaId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  // Copilot
  askCopilot: (
    investigationId: string,
    payload: { message: string; context_type?: string },
  ) =>
    request<CopilotResponse>(`/investigations/${investigationId}/copilot`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  applyCopilotEdits: (investigationId: string, edits: CopilotFieldEdit[]) =>
    request<Investigation>(`/investigations/${investigationId}/copilot/apply`, {
      method: 'POST',
      body: JSON.stringify({ edits }),
    }),
};
