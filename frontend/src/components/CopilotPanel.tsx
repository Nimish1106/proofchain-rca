import { useState, type FormEvent } from 'react';
import { Bot, Check, Send, Trash2, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchInvestigationById } from '../store/investigationsSlice';
import {
  applyCopilotSuggestedEdits,
  askCopilotQuestion,
  clearCopilotChat,
} from '../store/workspaceSlice';

interface CopilotPanelProps {
  investigationId: string;
  open: boolean;
  onClose: () => void;
}

export function CopilotPanel({
  investigationId,
  open,
  onClose,
}: CopilotPanelProps) {
  const dispatch = useAppDispatch();
  const history = useAppSelector((s) => s.workspace.copilotHistory);
  const running = useAppSelector((s) => s.workspace.runningCopilot);
  const [input, setInput] = useState('');

  if (!open) return null;

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || running) return;
    setInput('');
    await dispatch(
      askCopilotQuestion({
        investigationId,
        message,
        context_type: 'investigation',
      }),
    );
  };

  const handleApply = async (turnId: string, edits: NonNullable<(typeof history)[number]['suggestedEdits']>) => {
    await dispatch(
      applyCopilotSuggestedEdits({ investigationId, turnId, edits }),
    ).unwrap();
    await dispatch(fetchInvestigationById(investigationId));
  };

  return (
    <aside className="drawer-panel">
      <div className="card-header" style={{ background: '#0f172a', color: '#ffffff' }}>
        <div className="row">
          <Bot size={18} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>AI Investigation Copilot</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Q&A, summarization & targeted field edit proposals
            </div>
          </div>
        </div>
        <div className="row">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ color: '#cbd5e1' }}
            title="Clear chat"
            onClick={() => dispatch(clearCopilotChat())}
          >
            <Trash2 size={14} />
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ color: '#cbd5e1' }}
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div
        className="stack"
        style={{ flex: 1, overflowY: 'auto', padding: 14, background: 'var(--bg-subtle)' }}
      >
        {history.length === 0 && (
          <div className="alert alert-info" style={{ fontSize: 12 }}>
            <div>
              <strong>Try asking:</strong>
              <ul style={{ margin: '6px 0 0 16px', padding: 0 }}>
                <li>Summarize the confirmed evidence and open gaps.</li>
                <li>Update immediate containment to isolate Reactor R-204.</li>
                <li>What evidence is missing for Hypothesis 1?</li>
              </ul>
            </div>
          </div>
        )}

        {history.map((turn) => (
          <div
            key={turn.id}
            style={{
              alignSelf: turn.role === 'user' ? 'flex-end' : 'stretch',
              maxWidth: turn.role === 'user' ? '85%' : '100%',
              background: turn.role === 'user' ? 'var(--brand-primary)' : '#ffffff',
              color: turn.role === 'user' ? '#ffffff' : 'var(--text-primary)',
              border: turn.role === 'user' ? 'none' : '1px solid var(--border)',
              borderRadius: 10,
              padding: '10px 12px',
              fontSize: 13,
            }}
          >
            <div style={{ whiteSpace: 'pre-wrap' }}>{turn.text}</div>

            {turn.warnings && turn.warnings.length > 0 && (
              <div className="text-sm" style={{ marginTop: 8, color: 'var(--warning-text)' }}>
                {turn.warnings.map((w, idx) => (
                  <div key={idx}>Warning: {w}</div>
                ))}
              </div>
            )}

            {turn.suggestedEdits && turn.suggestedEdits.length > 0 && (
              <div className="stack" style={{ marginTop: 10 }}>
                {turn.suggestedEdits.map((edit, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border)',
                      borderRadius: 6,
                      padding: 8,
                      fontSize: 12,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>
                      Field: <code className="mono">{edit.field_name}</code>
                    </div>
                    <div className="text-muted">
                      Current: {edit.current_value ?? 'empty'}
                    </div>
                    <div style={{ color: '#15803d', fontWeight: 500 }}>
                      Suggested: {edit.suggested_value}
                    </div>
                    {edit.rationale && (
                      <div className="text-muted" style={{ marginTop: 3 }}>
                        {edit.rationale}
                      </div>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  disabled={turn.applied}
                  onClick={() => handleApply(turn.id, turn.suggestedEdits!)}
                >
                  <Check size={14} />
                  {turn.applied ? 'Edits Applied' : 'Apply Proposed Edits'}
                </button>
              </div>
            )}
          </div>
        ))}

        {running && (
          <div className="text-muted text-sm" style={{ padding: 6 }}>
            Copilot is analyzing investigation context...
          </div>
        )}
      </div>

      <form
        onSubmit={handleSend}
        style={{
          padding: 12,
          borderTop: '1px solid var(--border)',
          background: '#ffffff',
          display: 'flex',
          gap: 8,
        }}
      >
        <input
          className="input"
          placeholder="Ask Copilot or request a field edit..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={running}
        />
        <button type="submit" className="btn btn-primary" disabled={running || !input.trim()}>
          <Send size={14} />
        </button>
      </form>
    </aside>
  );
}
