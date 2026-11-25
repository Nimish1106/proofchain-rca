import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Edit3,
  Eye,
  FileText,
  GitBranch,
  History,
  Layers,
  Play,
  Plus,
  Save,
  ShieldAlert,
  Sparkles,
  Wrench,
  XCircle,
} from 'lucide-react';
import { CopilotPanel } from '../components/CopilotPanel';
import { DocumentIngestionModal } from '../components/DocumentIngestionModal';
import { DocumentViewerModal } from '../components/DocumentViewerModal';
import { EvidenceGraph } from '../components/EvidenceGraph';
import { StatusBadge } from '../components/StatusBadge';
import { useAppDispatch, useAppSelector } from '../store';
import {
  fetchInvestigationById,
  updateInvestigation,
} from '../store/investigationsSlice';
import {
  clearWorkspaceMessages,
  editWhyStepItem,
  fetchDocumentPreview,
  generateCapaItems,
  loadWorkspaceData,
  resolveGapItem,
  reviewEvidenceItem,
  reviewHypothesisItem,
  runFactExtraction,
  runRCAAnalysis,
  selectRCARun,
  updateCapaItemStatus,
} from '../store/workspaceSlice';
import type {
  CAPARecommendation,
  EvidenceGap,
  HypothesisDetail,
  HypothesisStatus,
  WhyStep,
} from '../types/api';

type WorkspaceTab =
  | 'evidence'
  | 'rca'
  | 'whys_graph'
  | 'gaps'
  | 'capa'
  | 'history';

const HYPOTHESIS_STATUSES: HypothesisStatus[] = [
  'proposed',
  'under_review',
  'supported_by_records',
  'contradicted',
  'rejected',
  'confirmed_by_investigator',
];

export function InvestigationWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const dispatch = useAppDispatch();

  const investigation = useAppSelector((s) => s.investigations.selected);
  const savingInvestigation = useAppSelector((s) => s.investigations.saving);
  const ws = useAppSelector((s) => s.workspace);

  const [activeTab, setActiveTab] = useState<WorkspaceTab>('evidence');
  const [evidenceFilter, setEvidenceFilter] = useState<'all' | 'source_excerpt' | 'extracted_fact'>('all');
  const [showIngest, setShowIngest] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);

  // Editable metadata overrides keyed by investigation.updated_at
  const [metaDraft, setMetaDraft] = useState<{
    version: string;
    values: {
      title: string;
      product_name: string;
      product_grade: string;
      batch_number: string;
      manufacturing_site: string;
      process_stage: string;
      incident_date: string;
      affected_quantity: string;
      affected_unit: string;
      incident_description: string;
      immediate_containment: string;
    };
  } | null>(null);

  const baseMeta = {
    title: investigation?.title ?? '',
    product_name: investigation?.product_name ?? '',
    product_grade: investigation?.product_grade ?? '',
    batch_number: investigation?.batch_number ?? '',
    manufacturing_site: investigation?.manufacturing_site ?? '',
    process_stage: investigation?.process_stage ?? '',
    incident_date: investigation?.incident_date ?? '',
    affected_quantity: investigation?.affected_quantity ?? '',
    affected_unit: investigation?.affected_unit ?? '',
    incident_description: investigation?.incident_description ?? '',
    immediate_containment: investigation?.immediate_containment ?? '',
  };

  const currentVersion = investigation
    ? `${investigation.id}:${investigation.updated_at}`
    : '';
  const metaForm =
    metaDraft && metaDraft.version === currentVersion ? metaDraft.values : baseMeta;

  const setMetaForm = (next: typeof baseMeta) => {
    setMetaDraft({ version: currentVersion, values: next });
  };

  useEffect(() => {
    if (!id) return;
    dispatch(fetchInvestigationById(id));
    dispatch(loadWorkspaceData(id));
  }, [dispatch, id]);

  if (!id) {
    return <div className="alert alert-danger">Missing investigation ID.</div>;
  }

  const handleSaveMeta = async (e: FormEvent) => {
    e.preventDefault();
    await dispatch(
      updateInvestigation({
        id,
        payload: {
          title: metaForm.title.trim(),
          product_name: metaForm.product_name.trim() || null,
          product_grade: metaForm.product_grade.trim() || null,
          batch_number: metaForm.batch_number.trim() || null,
          manufacturing_site: metaForm.manufacturing_site.trim() || null,
          process_stage: metaForm.process_stage.trim() || null,
          incident_date: metaForm.incident_date || null,
          affected_quantity: metaForm.affected_quantity
            ? Number(metaForm.affected_quantity)
            : null,
          affected_unit: metaForm.affected_unit.trim() || null,
          incident_description: metaForm.incident_description.trim() || null,
          immediate_containment: metaForm.immediate_containment.trim() || null,
        },
      }),
    );
  };

  const handleRunExtraction = async () => {
    await dispatch(runFactExtraction(id));
  };

  const handleRunRCA = async () => {
    const res = await dispatch(runRCAAnalysis(id));
    if (runRCAAnalysis.fulfilled.match(res)) {
      setActiveTab('rca');
    }
  };

  const handleGenerateCapa = async () => {
    const res = await dispatch(generateCapaItems(id));
    if (generateCapaItems.fulfilled.match(res)) {
      setActiveTab('capa');
    }
  };

  const filteredEvidence = ws.evidence.filter((e) =>
    evidenceFilter === 'all' ? true : e.evidence_kind === evidenceFilter,
  );

  const evidenceMap = new Map(ws.evidence.map((e) => [e.id, e]));

  const allGaps: Array<{ gap: EvidenceGap; scope: string }> = [];
  if (ws.activeRcaRun) {
    ws.activeRcaRun.hypotheses.forEach((h, idx) => {
      h.evidence_gaps.forEach((g) =>
        allGaps.push({ gap: g, scope: `H${idx + 1}: ${h.title}` }),
      );
    });
    ws.activeRcaRun.global_gaps.forEach((g) =>
      allGaps.push({ gap: g, scope: 'Global Investigation Gap' }),
    );
  }

  return (
    <div className="stack" style={{ gap: 16 }}>
      {/* Header Bar */}
      <div className="card card-body">
        <div className="row-between">
          <div>
            <Link to="/investigations" className="row text-sm text-muted" style={{ marginBottom: 4 }}>
              <ArrowLeft size={14} /> Back to Investigations
            </Link>
            <div className="row">
              <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
                {investigation?.title ?? 'Loading investigation...'}
              </h1>
              {investigation && <StatusBadge value={investigation.status} />}
            </div>
            {investigation && (
              <div className="row text-sm text-muted" style={{ marginTop: 4 }}>
                <span className="mono">ID: {investigation.id.slice(0, 8)}</span>
                {investigation.product_name && <span>• {investigation.product_name}</span>}
                {investigation.batch_number && (
                  <span className="mono">• Batch {investigation.batch_number}</span>
                )}
              </div>
            )}
          </div>

          <div className="row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowIngest(true)}
            >
              <Plus size={15} /> Add Source
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={ws.runningExtraction || ws.documents.length === 0}
              onClick={handleRunExtraction}
            >
              <Sparkles size={15} />
              {ws.runningExtraction ? 'Extracting...' : 'Extract Facts'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={ws.runningRca || ws.evidence.length === 0}
              onClick={handleRunRCA}
            >
              <Play size={15} />
              {ws.runningRca ? 'Running RCA...' : 'Run RCA Analysis'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={ws.runningCapa || !ws.activeRcaRun}
              onClick={handleGenerateCapa}
            >
              <Wrench size={15} />
              {ws.runningCapa ? 'Generating CAPA...' : 'Generate CAPA'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowCopilot((v) => !v)}
            >
              <Bot size={15} /> AI Copilot
            </button>
          </div>
        </div>
      </div>

      {/* Notices / Errors */}
      {ws.error && (
        <div className="alert alert-danger row-between">
          <span>{ws.error}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => dispatch(clearWorkspaceMessages())}
          >
            Dismiss
          </button>
        </div>
      )}
      {ws.notice && (
        <div className="alert alert-success row-between">
          <span>{ws.notice}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => dispatch(clearWorkspaceMessages())}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Two-Panel Workspace */}
      <div className="workspace-grid">
        {/* Left Panel: Investigation Record & Source Documents */}
        <div className="stack" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Investigation Details</h2>
              <span className="text-muted text-sm">Human-controlled</span>
            </div>
            <form onSubmit={handleSaveMeta} className="card-body stack">
              <div className="form-field">
                <label className="form-label">Title</label>
                <input
                  className="input"
                  value={metaForm.title}
                  onChange={(e) => setMetaForm({ ...metaForm, title: e.target.value })}
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label className="form-label">Product</label>
                  <input
                    className="input"
                    value={metaForm.product_name}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, product_name: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Grade</label>
                  <input
                    className="input"
                    value={metaForm.product_grade}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, product_grade: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Batch Number</label>
                  <input
                    className="input"
                    value={metaForm.batch_number}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, batch_number: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Incident Date</label>
                  <input
                    type="date"
                    className="input"
                    value={metaForm.incident_date}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, incident_date: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Site</label>
                  <input
                    className="input"
                    value={metaForm.manufacturing_site}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, manufacturing_site: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Process Stage</label>
                  <input
                    className="input"
                    value={metaForm.process_stage}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, process_stage: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Affected Qty</label>
                  <input
                    type="number"
                    step="0.001"
                    className="input"
                    value={metaForm.affected_quantity}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, affected_quantity: e.target.value })
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="form-label">Unit</label>
                  <input
                    className="input"
                    value={metaForm.affected_unit}
                    onChange={(e) =>
                      setMetaForm({ ...metaForm, affected_unit: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-field">
                <label className="form-label">Incident Description</label>
                <textarea
                  className="textarea"
                  rows={3}
                  value={metaForm.incident_description}
                  onChange={(e) =>
                    setMetaForm({ ...metaForm, incident_description: e.target.value })
                  }
                />
              </div>

              <div className="form-field">
                <label className="form-label">Immediate Containment</label>
                <textarea
                  className="textarea"
                  rows={2}
                  value={metaForm.immediate_containment}
                  onChange={(e) =>
                    setMetaForm({ ...metaForm, immediate_containment: e.target.value })
                  }
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={savingInvestigation}
              >
                <Save size={14} /> {savingInvestigation ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          {/* Source Documents */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Source Documents ({ws.documents.length})</h2>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setShowIngest(true)}
              >
                <Plus size={14} /> Add
              </button>
            </div>
            <div className="card-body stack">
              {ws.documents.length === 0 ? (
                <div className="text-muted text-sm">
                  No sources yet. Upload a PDF, paste a log, or ingest an email to begin.
                </div>
              ) : (
                ws.documents.map((doc) => (
                  <div
                    key={doc.id}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      padding: 10,
                      background: 'var(--bg-subtle)',
                    }}
                  >
                    <div className="row-between">
                      <div className="row" style={{ gap: 6, minWidth: 0 }}>
                        <FileText size={15} color="var(--brand-primary)" />
                        <strong
                          style={{
                            fontSize: 13,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {doc.original_filename}
                        </strong>
                      </div>
                      <StatusBadge value={doc.document_type} />
                    </div>
                    <div className="row-between text-sm text-muted" style={{ marginTop: 6 }}>
                      <span>
                        {doc.page_count} page{doc.page_count === 1 ? '' : 's'} •{' '}
                        {doc.extraction_status.replace(/_/g, ' ')}
                      </span>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() =>
                          dispatch(fetchDocumentPreview({ investigationId: id, documentId: doc.id }))
                        }
                      >
                        <Eye size={13} /> View
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Panel: Tabbed Evidence, RCA, 5-Whys/Graph, Gaps, CAPA, History */}
        <div className="card">
          <div className="tabs-bar">
            <button
              type="button"
              className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
              onClick={() => setActiveTab('evidence')}
            >
              <Layers size={15} /> Evidence ({ws.evidence.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'rca' ? 'active' : ''}`}
              onClick={() => setActiveTab('rca')}
            >
              <AlertTriangle size={15} /> RCA Hypotheses (
              {ws.activeRcaRun?.hypotheses.length ?? 0})
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'whys_graph' ? 'active' : ''}`}
              onClick={() => setActiveTab('whys_graph')}
            >
              <GitBranch size={15} /> 5-Whys & Graph
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'gaps' ? 'active' : ''}`}
              onClick={() => setActiveTab('gaps')}
            >
              <ShieldAlert size={15} /> Evidence Gaps ({allGaps.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'capa' ? 'active' : ''}`}
              onClick={() => setActiveTab('capa')}
            >
              <Wrench size={15} /> CAPA ({ws.capas.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              <History size={15} /> Runs ({ws.rcaRuns.length})
            </button>
          </div>

          <div className="card-body stack" style={{ gap: 16 }}>
            {/* TAB 1: EVIDENCE & EXTRACTION */}
            {activeTab === 'evidence' && (
              <>
                <div className="row-between">
                  <div className="row">
                    {(['all', 'source_excerpt', 'extracted_fact'] as const).map((kind) => (
                      <button
                        key={kind}
                        type="button"
                        className={`btn btn-sm ${
                          evidenceFilter === kind ? 'btn-primary' : 'btn-secondary'
                        }`}
                        onClick={() => setEvidenceFilter(kind)}
                      >
                        {kind === 'all'
                          ? 'All Evidence'
                          : kind === 'source_excerpt'
                            ? 'Source Excerpts'
                            : 'Extracted Facts'}
                      </button>
                    ))}
                  </div>
                  <span className="text-muted text-sm">
                    Pending extracted facts cannot support hypotheses until accepted.
                  </span>
                </div>

                {ws.lastExtraction && ws.lastExtraction.field_conflicts.length > 0 && (
                  <div className="alert alert-warning" style={{ flexDirection: 'column', gap: 10 }}>
                    <strong>
                      Conflicting Extracted Values Detected ({ws.lastExtraction.field_conflicts.length})
                    </strong>
                    {ws.lastExtraction.field_conflicts.map((conflict, idx) => (
                      <div key={idx} style={{ width: '100%' }}>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>
                          Field: <code className="mono">{conflict.field_name}</code>
                        </div>
                        <div className="row" style={{ marginTop: 6 }}>
                          {conflict.candidates.map((c, cIdx) => (
                            <button
                              key={cIdx}
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() =>
                                dispatch(
                                  updateInvestigation({
                                    id,
                                    payload: { [conflict.field_name]: c.value },
                                  }),
                                )
                              }
                            >
                              Apply "{c.value}" ({c.original_filename}, p.{c.page_number})
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {filteredEvidence.length === 0 ? (
                  <div className="text-muted">
                    No evidence records in this filter yet. Add a source document or run Fact Extraction.
                  </div>
                ) : (
                  <div className="stack">
                    {filteredEvidence.map((ev) => (
                      <div
                        key={ev.id}
                        style={{
                          border: '1px solid var(--border)',
                          borderRadius: 8,
                          padding: 12,
                          background: '#ffffff',
                        }}
                      >
                        <div className="row-between">
                          <div className="row">
                            <StatusBadge value={ev.evidence_kind} />
                            <StatusBadge value={ev.review_status} />
                            {ev.field_name && (
                              <code className="mono" style={{ fontSize: 12 }}>
                                {ev.field_name}: {ev.extracted_value}
                              </code>
                            )}
                          </div>
                          <span className="text-muted text-sm">
                            {ev.page_number ? `Page ${ev.page_number}` : ''} •{' '}
                            <span className="mono">{ev.id.slice(0, 8)}</span>
                          </span>
                        </div>

                        <p
                          style={{
                            margin: '8px 0',
                            fontSize: 13,
                            color: 'var(--text-primary)',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {ev.content}
                        </p>

                        <div className="row" style={{ justifyContent: 'flex-end' }}>
                          {ev.review_status !== 'accepted' && (
                            <button
                              type="button"
                              className="btn btn-success btn-sm"
                              onClick={() =>
                                dispatch(
                                  reviewEvidenceItem({
                                    investigationId: id,
                                    evidenceId: ev.id,
                                    review_status: 'accepted',
                                  }),
                                )
                              }
                            >
                              <Check size={13} /> Accept
                            </button>
                          )}
                          {ev.evidence_kind === 'extracted_fact' && (
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              onClick={async () => {
                                await dispatch(
                                  reviewEvidenceItem({
                                    investigationId: id,
                                    evidenceId: ev.id,
                                    review_status: 'accepted',
                                    apply_to_investigation: true,
                                  }),
                                );
                                await dispatch(fetchInvestigationById(id));
                              }}
                            >
                              <CheckCircle2 size={13} /> Accept & Apply Field
                            </button>
                          )}
                          {ev.review_status !== 'rejected' && (
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() =>
                                dispatch(
                                  reviewEvidenceItem({
                                    investigationId: id,
                                    evidenceId: ev.id,
                                    review_status: 'rejected',
                                  }),
                                )
                              }
                            >
                              <XCircle size={13} /> Reject
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* TAB 2: RCA HYPOTHESES */}
            {activeTab === 'rca' && (
              <>
                <div className="alert alert-warning">
                  <AlertTriangle size={16} />
                  <span>
                    AI-generated hypotheses remain <strong>proposed</strong> until reviewed and
                    confirmed by a qualified human investigator.
                  </span>
                </div>

                {!ws.activeRcaRun ? (
                  <div className="text-muted">
                    No completed RCA run yet. Click <strong>Run RCA Analysis</strong> above once
                    source evidence is available.
                  </div>
                ) : (
                  <div className="stack" style={{ gap: 16 }}>
                    <div
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        padding: 14,
                        background: 'var(--bg-subtle)',
                      }}
                    >
                      <div className="row-between">
                        <strong>Run Summary</strong>
                        <div className="row text-sm text-muted">
                          <span className="mono">{ws.activeRcaRun.model_name}</span>
                          <StatusBadge value={ws.activeRcaRun.status} />
                        </div>
                      </div>
                      <p style={{ margin: '8px 0 0', fontSize: 13 }}>
                        {ws.activeRcaRun.summary ?? 'No summary available.'}
                      </p>
                    </div>

                    {ws.activeRcaRun.hypotheses.map((hyp, idx) => (
                      <HypothesisReviewCard
                        key={`${hyp.id}:${hyp.updated_at}`}
                        index={idx + 1}
                        hypothesis={hyp}
                        evidenceMap={evidenceMap}
                        onSaveReview={(status, reviewNote) =>
                          dispatch(
                            reviewHypothesisItem({
                              investigationId: id,
                              hypothesisId: hyp.id,
                              status,
                              review_note: reviewNote,
                            }),
                          )
                        }
                      />
                    ))}
                  </div>
                )}
              </>
            )}

            {/* TAB 3: 5-WHYS & GRAPH */}
            {activeTab === 'whys_graph' && (
              <div className="stack" style={{ gap: 18 }}>
                <div>
                  <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>
                    Interactive Evidence-to-Hypothesis Causal Graph
                  </h3>
                  <EvidenceGraph
                    investigationTitle={investigation?.title ?? 'Investigation'}
                    rcaRun={ws.activeRcaRun}
                    evidence={ws.evidence}
                    capas={ws.capas}
                  />
                </div>

                {ws.activeRcaRun &&
                  ws.activeRcaRun.hypotheses.map((hyp, idx) => (
                    <div
                      key={hyp.id}
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        padding: 14,
                      }}
                    >
                      <div className="row-between" style={{ marginBottom: 10 }}>
                        <strong>
                          H{idx + 1}: {hyp.title} — 5-Whys Causal Chain
                        </strong>
                        <StatusBadge value={hyp.status} />
                      </div>
                      <div className="stack">
                        {hyp.why_steps.map((step) => (
                          <WhyStepEditorRow
                            key={`${step.id}:${step.updated_at}`}
                            step={step}
                            citedEvidence={
                              step.evidence_item_id
                                ? evidenceMap.get(step.evidence_item_id)?.content
                                : undefined
                            }
                            onSave={(question, answer) =>
                              dispatch(
                                editWhyStepItem({
                                  investigationId: id,
                                  stepId: step.id,
                                  question,
                                  answer,
                                }),
                              )
                            }
                          />
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            )}

            {/* TAB 4: EVIDENCE GAPS */}
            {activeTab === 'gaps' && (
              <div className="stack">
                {allGaps.length === 0 ? (
                  <div className="text-muted">
                    No evidence gaps recorded yet. Run an RCA analysis to surface open gaps.
                  </div>
                ) : (
                  allGaps.map(({ gap, scope }) => (
                    <GapCard
                      key={gap.id}
                      gap={gap}
                      scope={scope}
                      onUpdate={(status, resolutionNote) =>
                        dispatch(
                          resolveGapItem({
                            investigationId: id,
                            gapId: gap.id,
                            status,
                            resolution_note: resolutionNote,
                          }),
                        )
                      }
                    />
                  ))
                )}
              </div>
            )}

            {/* TAB 5: CAPA MANAGEMENT */}
            {activeTab === 'capa' && (
              <div className="stack">
                {ws.capas.length === 0 ? (
                  <div className="text-muted">
                    No CAPA recommendations generated yet. Confirm or review hypotheses, then click{' '}
                    <strong>Generate CAPA</strong>.
                  </div>
                ) : (
                  ws.capas.map((capa) => (
                    <CapaCard
                      key={capa.id}
                      capa={capa}
                      onUpdateStatus={(status, reviewNote) =>
                        dispatch(
                          updateCapaItemStatus({
                            investigationId: id,
                            capaId: capa.id,
                            status,
                            review_note: reviewNote,
                          }),
                        )
                      }
                    />
                  ))
                )}
              </div>
            )}

            {/* TAB 6: ANALYSIS RUN HISTORY */}
            {activeTab === 'history' && (
              <div className="table-wrap">
                {ws.rcaRuns.length === 0 ? (
                  <div className="text-muted">No RCA runs executed for this investigation yet.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Started</th>
                        <th>Model</th>
                        <th>Status</th>
                        <th>Fingerprint</th>
                        <th>Error</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {ws.rcaRuns.map((run) => (
                        <tr key={run.id}>
                          <td className="text-sm">
                            {new Date(run.created_at).toLocaleString()}
                          </td>
                          <td className="mono text-sm">{run.model_name}</td>
                          <td>
                            <StatusBadge value={run.status} />
                          </td>
                          <td className="mono text-sm">{run.input_fingerprint.slice(0, 12)}...</td>
                          <td className="text-sm">{run.error_code ?? '—'}</td>
                          <td style={{ textAlign: 'right' }}>
                            {run.status === 'completed' && (
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={async () => {
                                  await dispatch(
                                    selectRCARun({ investigationId: id, runId: run.id }),
                                  );
                                  setActiveTab('rca');
                                }}
                              >
                                Inspect Run
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {showIngest && (
        <DocumentIngestionModal
          investigationId={id}
          onClose={() => setShowIngest(false)}
        />
      )}

      <DocumentViewerModal investigationId={id} />

      <CopilotPanel
        investigationId={id}
        open={showCopilot}
        onClose={() => setShowCopilot(false)}
      />
    </div>
  );
}

function HypothesisReviewCard({
  index,
  hypothesis,
  evidenceMap,
  onSaveReview,
}: {
  index: number;
  hypothesis: HypothesisDetail;
  evidenceMap: Map<string, { content: string; field_name: string | null; extracted_value: string | null }>;
  onSaveReview: (status: HypothesisStatus, reviewNote: string) => void;
}) {
  const [status, setStatus] = useState<HypothesisStatus>(
    hypothesis.status as HypothesisStatus,
  );
  const [note, setNote] = useState(hypothesis.review_note ?? '');

  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: 16,
        background: '#ffffff',
      }}
    >
      <div className="row-between">
        <div className="row">
          <strong style={{ fontSize: 15 }}>
            H{index}: {hypothesis.title}
          </strong>
          <StatusBadge value={hypothesis.status} />
        </div>
        {hypothesis.reviewed_at && (
          <span className="text-muted text-sm">
            Reviewed {new Date(hypothesis.reviewed_at).toLocaleString()}
          </span>
        )}
      </div>

      <p style={{ margin: '8px 0', fontSize: 13 }}>{hypothesis.description}</p>
      {hypothesis.causal_mechanism && (
        <div className="text-sm text-muted" style={{ marginBottom: 10 }}>
          <strong>Causal Mechanism:</strong> {hypothesis.causal_mechanism}
        </div>
      )}

      {hypothesis.evidence_links.length > 0 && (
        <div className="stack" style={{ gap: 6, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>Linked Evidence</div>
          {hypothesis.evidence_links.map((link) => {
            const ev = evidenceMap.get(link.evidence_item_id);
            return (
              <div
                key={link.id}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: 8,
                  background: 'var(--bg-subtle)',
                  fontSize: 12,
                }}
              >
                <div className="row">
                  <StatusBadge value={link.relationship_type} />
                  <span>{link.rationale}</span>
                </div>
                {ev && (
                  <div className="text-muted" style={{ marginTop: 4 }}>
                    "{ev.content.slice(0, 180)}"
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div
        className="row"
        style={{
          paddingTop: 10,
          borderTop: '1px solid var(--border)',
          alignItems: 'flex-end',
        }}
      >
        <div className="form-field" style={{ width: 220 }}>
          <label className="form-label">Review Decision</label>
          <select
            className="select"
            value={status}
            onChange={(e) => setStatus(e.target.value as HypothesisStatus)}
          >
            {HYPOTHESIS_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field" style={{ flex: 1, minWidth: 200 }}>
          <label className="form-label">Investigator Review Note</label>
          <input
            className="input"
            placeholder="Document basis for status decision..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onSaveReview(status, note)}
        >
          <Save size={14} /> Update Review
        </button>
      </div>
    </div>
  );
}

function WhyStepEditorRow({
  step,
  citedEvidence,
  onSave,
}: {
  step: WhyStep;
  citedEvidence?: string;
  onSave: (question: string, answer: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState(step.question);
  const [answer, setAnswer] = useState(step.answer ?? '');

  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: 10,
        background: 'var(--bg-subtle)',
      }}
    >
      <div className="row-between">
        <div className="row">
          <strong style={{ fontSize: 12 }}>Why #{step.step_number}</strong>
          <StatusBadge value={step.answer_basis} />
        </div>
        {!editing ? (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setEditing(true)}
          >
            <Edit3 size={13} /> Edit
          </button>
        ) : (
          <div className="row">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => {
                onSave(question, answer);
                setEditing(false);
              }}
            >
              <Save size={13} /> Save
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {editing ? (
        <div className="stack" style={{ marginTop: 8 }}>
          <input
            className="input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <textarea
            className="textarea"
            rows={2}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
        </div>
      ) : (
        <div style={{ marginTop: 6, fontSize: 13 }}>
          <div style={{ fontWeight: 500 }}>{step.question}</div>
          <div className="text-muted" style={{ marginTop: 3 }}>
            Answer: {step.answer ?? 'Unknown'}
          </div>
          {citedEvidence && (
            <div className="text-sm text-muted" style={{ marginTop: 4 }}>
              Cited Excerpt: "{citedEvidence.slice(0, 160)}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function GapCard({
  gap,
  scope,
  onUpdate,
}: {
  gap: EvidenceGap;
  scope: string;
  onUpdate: (status: 'open' | 'addressed' | 'waived', note: string) => void;
}) {
  const [note, setNote] = useState(gap.resolution_note ?? '');

  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 14,
        background: '#ffffff',
      }}
    >
      <div className="row-between">
        <div className="row">
          <StatusBadge value={gap.priority} />
          <StatusBadge value={gap.status} />
          <span className="text-sm text-muted">{scope}</span>
        </div>
        <span className="text-sm text-muted">{gap.gap_type.replace(/_/g, ' ')}</span>
      </div>
      <p style={{ margin: '8px 0 4px', fontSize: 13, fontWeight: 500 }}>
        {gap.description}
      </p>
      {gap.recommended_question && (
        <div className="text-sm text-muted">
          Recommended follow-up: {gap.recommended_question}
        </div>
      )}
      <div className="row" style={{ marginTop: 10 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder="Resolution / waiver justification note..."
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-success btn-sm"
          onClick={() => onUpdate('addressed', note)}
        >
          Mark Addressed
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onUpdate('waived', note)}
        >
          Waive
        </button>
        {gap.status !== 'open' && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onUpdate('open', note)}
          >
            Reopen
          </button>
        )}
      </div>
    </div>
  );
}

function CapaCard({
  capa,
  onUpdateStatus,
}: {
  capa: CAPARecommendation;
  onUpdateStatus: (status: string, note: string) => void;
}) {
  const [note, setNote] = useState(capa.review_note ?? '');

  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: 16,
        background: '#ffffff',
      }}
    >
      <div className="row-between">
        <div className="row">
          <strong style={{ fontSize: 15 }}>{capa.title}</strong>
          <StatusBadge value={capa.capa_type} />
          <StatusBadge value={capa.priority} />
          <StatusBadge value={capa.status} />
        </div>
      </div>

      <p style={{ margin: '8px 0', fontSize: 13 }}>{capa.description}</p>

      <div className="form-grid text-sm" style={{ background: 'var(--bg-subtle)', padding: 10, borderRadius: 6 }}>
        <div>
          <strong>Expected Outcome:</strong> {capa.expected_outcome ?? '—'}
        </div>
        <div>
          <strong>Verification Method:</strong> {capa.verification_method ?? '—'}
        </div>
        <div>
          <strong>Effectiveness Criteria:</strong> {capa.effectiveness_criteria ?? '—'}
        </div>
        <div>
          <strong>Residual Risk:</strong> {capa.residual_risk ?? '—'}
        </div>
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder="QA review / approval note..."
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-success btn-sm"
          onClick={() => onUpdateStatus('approved', note)}
        >
          Approve
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => onUpdateStatus('in_progress', note)}
        >
          In Progress
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onUpdateStatus('completed', note)}
        >
          Complete
        </button>
        <button
          type="button"
          className="btn btn-danger btn-sm"
          onClick={() => onUpdateStatus('rejected', note)}
        >
          Reject
        </button>
      </div>
    </div>
  );
}
