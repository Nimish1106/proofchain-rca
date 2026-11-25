export interface Investigation {
  id: string;
  title: string;
  status: string;
  product_name: string | null;
  product_grade: string | null;
  batch_number: string | null;
  manufacturing_site: string | null;
  process_stage: string | null;
  incident_date: string | null;
  affected_quantity: string | null;
  affected_unit: string | null;
  incident_description: string | null;
  immediate_containment: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvestigationCreatePayload {
  title: string;
  product_name?: string | null;
  product_grade?: string | null;
  batch_number?: string | null;
  manufacturing_site?: string | null;
  process_stage?: string | null;
  incident_date?: string | null;
  affected_quantity?: number | string | null;
  affected_unit?: string | null;
  incident_description?: string | null;
  immediate_containment?: string | null;
}

export type InvestigationUpdatePayload = Partial<InvestigationCreatePayload>;

export interface InvestigationListResponse {
  items: Investigation[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceDocument {
  id: string;
  investigation_id: string;
  document_type: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  sha256: string;
  page_count: number;
  extraction_status: string;
  created_at: string;
}

export interface DocumentUploadResponse {
  document: SourceDocument;
  evidence_items_created: number;
  pages_without_text: number[];
  extracted_text_characters: number;
}

export interface DocumentPageContent {
  evidence_id: string;
  page_number: number | null;
  content: string;
}

export interface DocumentContentResponse {
  document_id: string;
  document_type: string;
  original_filename: string;
  page_count: number;
  extraction_status: string;
  pages: DocumentPageContent[];
}

export interface EvidenceItem {
  id: string;
  investigation_id: string;
  source_document_id: string;
  evidence_kind: 'source_excerpt' | 'extracted_fact' | string;
  content: string;
  page_number: number | null;
  source_start_char: number | null;
  source_end_char: number | null;
  field_name: string | null;
  extracted_value: string | null;
  review_status: 'pending' | 'accepted' | 'rejected' | string;
  created_at: string;
}

export interface ExtractedFactResult {
  id: string;
  source_document_id: string;
  field_name: string;
  extracted_value: string;
  content: string;
  page_number: number;
  source_start_char: number;
  source_end_char: number;
  review_status: string;
}

export interface RejectedFactResult {
  field_name: string;
  extracted_value: string;
  source_quote: string;
  page_number: number;
  reason: string;
}

export interface ConflictCandidate {
  value: string;
  source_document_id: string;
  original_filename: string;
  page_number: number;
  source_quote: string;
}

export interface FieldConflict {
  field_name: string;
  status: string;
  candidates: ConflictCandidate[];
}

export interface ExtractionRunResponse {
  investigation_id: string;
  status: string;
  summaries: string[];
  extracted_facts: ExtractedFactResult[];
  validated_fact_count: number;
  new_facts_count: number;
  duplicate_facts_count: number;
  rejected_facts: RejectedFactResult[];
  field_conflicts: FieldConflict[];
  warnings: string[];
}

export interface HypothesisEvidenceLink {
  id: string;
  evidence_item_id: string;
  relationship_type: 'supports' | 'contradicts' | 'contextual' | string;
  rationale: string;
  created_at: string;
}

export interface WhyStep {
  id: string;
  hypothesis_id: string;
  step_number: number;
  question: string;
  answer: string | null;
  answer_basis: 'source_supported' | 'hypothesis' | 'unknown' | string;
  evidence_item_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvidenceGap {
  id: string;
  investigation_id: string;
  analysis_run_id: string;
  hypothesis_id: string | null;
  gap_type: string;
  description: string;
  recommended_question: string | null;
  priority: 'low' | 'medium' | 'high' | string;
  status: 'open' | 'addressed' | 'waived' | string;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export type HypothesisStatus =
  | 'proposed'
  | 'under_review'
  | 'supported_by_records'
  | 'contradicted'
  | 'rejected'
  | 'confirmed_by_investigator';

export interface HypothesisDetail {
  id: string;
  investigation_id: string;
  analysis_run_id: string;
  title: string;
  description: string;
  causal_mechanism: string | null;
  status: HypothesisStatus | string;
  review_note: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  evidence_links: HypothesisEvidenceLink[];
  why_steps: WhyStep[];
  evidence_gaps: EvidenceGap[];
}

export interface RCARunSummary {
  id: string;
  investigation_id: string;
  model_name: string;
  input_fingerprint: string;
  status: 'running' | 'completed' | 'failed' | string;
  summary: string | null;
  error_code: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface RCARunDetail extends RCARunSummary {
  hypotheses: HypothesisDetail[];
  global_gaps: EvidenceGap[];
}

export interface CAPARecommendation {
  id: string;
  investigation_id: string;
  hypothesis_id: string;
  capa_type: 'corrective' | 'preventive' | string;
  title: string;
  description: string;
  expected_outcome: string | null;
  verification_method: string | null;
  effectiveness_criteria: string | null;
  priority: 'low' | 'medium' | 'high' | 'critical' | string;
  residual_risk: string | null;
  status: 'proposed' | 'approved' | 'in_progress' | 'completed' | 'rejected' | string;
  review_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CopilotFieldEdit {
  field_name: string;
  current_value: string | null;
  suggested_value: string;
  rationale: string;
}

export interface CopilotResponse {
  message: string;
  suggested_edits: CopilotFieldEdit[];
  warnings: string[];
}
