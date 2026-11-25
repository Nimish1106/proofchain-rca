import { Download, FileText, X } from 'lucide-react';
import { apiClient } from '../api/client';
import { useAppDispatch, useAppSelector } from '../store';
import { closeDocumentPreview } from '../store/workspaceSlice';
import { StatusBadge } from './StatusBadge';

export function DocumentViewerModal({ investigationId }: { investigationId: string }) {
  const dispatch = useAppDispatch();
  const preview = useAppSelector((s) => s.workspace.documentPreview);

  if (!preview) return null;

  const downloadUrl = apiClient.getDocumentDownloadUrl(
    investigationId,
    preview.document_id,
  );

  return (
    <div className="modal-backdrop">
      <div className="modal-panel" style={{ maxWidth: 820 }}>
        <div className="card-header">
          <div className="row">
            <FileText size={18} />
            <div>
              <h3 className="card-title">{preview.original_filename}</h3>
              <div className="row text-sm text-muted" style={{ marginTop: 2 }}>
                <span>Type: {preview.document_type.toUpperCase()}</span>
                <span>Pages: {preview.page_count}</span>
                <StatusBadge value={preview.extraction_status} />
              </div>
            </div>
          </div>
          <div className="row">
            <a
              href={downloadUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary btn-sm"
            >
              <Download size={14} /> Download Original
            </a>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => dispatch(closeDocumentPreview())}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="card-body stack" style={{ overflowY: 'auto' }}>
          {preview.pages.length === 0 ? (
            <div className="alert alert-warning">
              No machine-readable text excerpts were extracted for this document.
            </div>
          ) : (
            preview.pages.map((page) => (
              <div
                key={page.evidence_id}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: 12,
                  background: 'var(--bg-subtle)',
                }}
              >
                <div className="row-between" style={{ marginBottom: 6 }}>
                  <strong style={{ fontSize: 12 }}>
                    Page {page.page_number ?? 1}
                  </strong>
                  <span className="mono text-muted" style={{ fontSize: 11 }}>
                    Evidence ID: {page.evidence_id.slice(0, 8)}...
                  </span>
                </div>
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: 'pre-wrap',
                    fontSize: 12,
                    lineHeight: 1.55,
                    color: 'var(--text-primary)',
                  }}
                >
                  {page.content}
                </pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
