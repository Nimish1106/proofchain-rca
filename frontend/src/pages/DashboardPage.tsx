import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
  Plus,
  ShieldCheck,
} from 'lucide-react';
import { CreateInvestigationModal } from '../components/CreateInvestigationModal';
import { StatusBadge } from '../components/StatusBadge';
import { useAppDispatch, useAppSelector } from '../store';
import { checkApiHealth, fetchInvestigations } from '../store/investigationsSlice';

export function DashboardPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { items, total, loading, apiHealthy, error } = useAppSelector(
    (s) => s.investigations,
  );
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    dispatch(checkApiHealth());
    dispatch(fetchInvestigations());
  }, [dispatch]);

  const draftCount = items.filter((i) => i.status === 'draft').length;
  const activeCount = items.filter(
    (i) => i.status === 'in_progress' || i.status === 'processing' || i.status === 'in_review',
  ).length;
  const completedCount = items.filter((i) => i.status === 'completed').length;

  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="row-between">
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>
            ProofChain RCA Command Center
          </h1>
          <p className="text-muted" style={{ margin: '4px 0 0' }}>
            Evidence-first root cause analysis & CAPA engineering for pharmaceutical API manufacturing
          </p>
        </div>
        <div className="row">
          <span
            className={`badge ${apiHealthy ? 'badge-success' : apiHealthy === false ? 'badge-danger' : 'badge-neutral'}`}
          >
            <Activity size={12} />
            {apiHealthy ? 'API Connected' : apiHealthy === false ? 'API Offline' : 'Checking API...'}
          </span>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowCreate(true)}
          >
            <Plus size={16} /> New Investigation
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="kpi-grid">
        <div className="card card-body">
          <div className="row-between">
            <span className="text-muted text-sm">Total Investigations</span>
            <ClipboardList size={18} color="var(--brand-primary)" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>{total}</div>
        </div>
        <div className="card card-body">
          <div className="row-between">
            <span className="text-muted text-sm">Draft / Intake</span>
            <FlaskConical size={18} color="#d97706" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>{draftCount}</div>
        </div>
        <div className="card card-body">
          <div className="row-between">
            <span className="text-muted text-sm">Active Analysis</span>
            <ShieldCheck size={18} color="var(--brand-accent)" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>{activeCount}</div>
        </div>
        <div className="card card-body">
          <div className="row-between">
            <span className="text-muted text-sm">Completed</span>
            <CheckCircle2 size={18} color="#16a34a" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>{completedCount}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Recent Investigations</h2>
          <Link to="/investigations" className="btn btn-ghost btn-sm">
            View All <ArrowRight size={14} />
          </Link>
        </div>
        <div className="table-wrap">
          {loading ? (
            <div className="card-body text-muted">Loading investigations...</div>
          ) : items.length === 0 ? (
            <div className="card-body">
              <p className="text-muted" style={{ margin: '0 0 12px' }}>
                No investigations created yet. Start by creating your first deviation investigation.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowCreate(true)}
              >
                <Plus size={15} /> Create First Investigation
              </button>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Product & Batch</th>
                  <th>Site / Stage</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.slice(0, 8).map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <Link
                        to={`/investigations/${inv.id}`}
                        style={{ fontWeight: 600, color: 'var(--text-primary)' }}
                      >
                        {inv.title}
                      </Link>
                    </td>
                    <td>
                      <div>{inv.product_name ?? '—'}</div>
                      <div className="text-muted text-sm mono">
                        {inv.batch_number ?? 'No batch'}
                      </div>
                    </td>
                    <td>
                      <div>{inv.manufacturing_site ?? '—'}</div>
                      <div className="text-muted text-sm">{inv.process_stage ?? ''}</div>
                    </td>
                    <td>
                      <StatusBadge value={inv.status} />
                    </td>
                    <td className="text-muted text-sm">
                      {new Date(inv.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Link
                        to={`/investigations/${inv.id}`}
                        className="btn btn-secondary btn-sm"
                      >
                        Open Workspace
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateInvestigationModal
          onClose={() => setShowCreate(false)}
          onCreated={(id) => navigate(`/investigations/${id}`)}
        />
      )}
    </div>
  );
}
