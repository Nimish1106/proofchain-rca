import { useState, type FormEvent } from 'react';
import { FileUp, Mail, FileText, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  ingestEmailSource,
  ingestTextSource,
  uploadPdfDocument,
} from '../store/workspaceSlice';

interface DocumentIngestionModalProps {
  investigationId: string;
  onClose: () => void;
}

type IngestionMode = 'pdf' | 'text' | 'email';

export function DocumentIngestionModal({
  investigationId,
  onClose,
}: DocumentIngestionModalProps) {
  const dispatch = useAppDispatch();
  const ingesting = useAppSelector((s) => s.workspace.ingesting);

  const [mode, setMode] = useState<IngestionMode>('pdf');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailSender, setEmailSender] = useState('');
  const [emailDate, setEmailDate] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    try {
      if (mode === 'pdf') {
        if (!pdfFile) {
          setLocalError('Select a PDF file to upload.');
          return;
        }
        await dispatch(uploadPdfDocument({ investigationId, file: pdfFile })).unwrap();
      } else if (mode === 'text') {
        if (!textTitle.trim() || !textContent.trim()) {
          setLocalError('Title and text content are required.');
          return;
        }
        await dispatch(
          ingestTextSource({
            investigationId,
            title: textTitle.trim(),
            content: textContent.trim(),
          }),
        ).unwrap();
      } else {
        if (!emailSubject.trim() || !emailSender.trim() || !emailBody.trim()) {
          setLocalError('Subject, sender, and email body are required.');
          return;
        }
        await dispatch(
          ingestEmailSource({
            investigationId,
            subject: emailSubject.trim(),
            sender: emailSender.trim(),
            date: emailDate.trim() || undefined,
            body: emailBody.trim(),
          }),
        ).unwrap();
      }
      onClose();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Ingestion failed');
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-panel">
        <div className="card-header">
          <h3 className="card-title">Add Investigation Source Document</h3>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="tabs-bar" style={{ paddingLeft: 18 }}>
          <button
            type="button"
            className={`tab-btn ${mode === 'pdf' ? 'active' : ''}`}
            onClick={() => setMode('pdf')}
          >
            <FileUp size={15} /> PDF Upload
          </button>
          <button
            type="button"
            className={`tab-btn ${mode === 'text' ? 'active' : ''}`}
            onClick={() => setMode('text')}
          >
            <FileText size={15} /> Paste Text / Log
          </button>
          <button
            type="button"
            className={`tab-btn ${mode === 'email' ? 'active' : ''}`}
            onClick={() => setMode('email')}
          >
            <Mail size={15} /> Ingest Email
          </button>
        </div>

        <form onSubmit={handleSubmit} className="card-body stack" style={{ overflowY: 'auto' }}>
          {localError && <div className="alert alert-danger">{localError}</div>}

          {mode === 'pdf' && (
            <div className="form-field">
              <label className="form-label">Batch Record / Deviation PDF</label>
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="input"
                onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
              />
              <span className="text-muted text-sm">
                PDFs are extracted page-by-page into traceable source excerpts.
              </span>
            </div>
          )}

          {mode === 'text' && (
            <>
              <div className="form-field">
                <label className="form-label">Document Title</label>
                <input
                  className="input"
                  placeholder="e.g., Operator Shift Log — Reactor R-204"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label className="form-label">Source Text Content</label>
                <textarea
                  className="textarea"
                  rows={8}
                  placeholder="Paste deviation notes, sensor log excerpts, or lab observations..."
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                />
              </div>
            </>
          )}

          {mode === 'email' && (
            <div className="form-grid">
              <div className="form-field full">
                <label className="form-label">Email Subject</label>
                <input
                  className="input"
                  placeholder="e.g., RE: Batch 2026-04 Cooling Deviation"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label className="form-label">Sender</label>
                <input
                  className="input"
                  placeholder="qa.lead@pharma.example"
                  value={emailSender}
                  onChange={(e) => setEmailSender(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label className="form-label">Date (optional)</label>
                <input
                  className="input"
                  placeholder="2026-11-20"
                  value={emailDate}
                  onChange={(e) => setEmailDate(e.target.value)}
                />
              </div>
              <div className="form-field full">
                <label className="form-label">Email Body</label>
                <textarea
                  className="textarea"
                  rows={7}
                  placeholder="Paste full email message body..."
                  value={emailBody}
                  onChange={(e) => setEmailBody(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="row" style={{ justifyContent: 'flex-end', marginTop: 6 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={ingesting}>
              {ingesting ? 'Ingesting...' : 'Ingest Source'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
