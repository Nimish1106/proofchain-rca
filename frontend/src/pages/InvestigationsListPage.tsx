import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { CreateInvestigationModal } from '../components/CreateInvestigationModal';
import { StatusBadge } from '../components/StatusBadge';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchInvestigations } from '../store/investigationsSlice';

export function InvestigationsListPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { items, loading, error } = useAppSelector((s) => s.investigations);

  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    dispatch(fetchInvestigations());
  }, [dispatch]);

  const filtered = items.filter((inv) => {
    if (statusFilter !== 'all' && inv.status !== statusFilter) return false;
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      inv.title.toLowerCase().includes(q) ||
      (inv.product_name?.toLowerCase().includes(q) ?? false) ||
      (inv.batch_number?.toLowerCase().includes(q) ?? false) ||
      (inv.manufacturing_site?.toLowerCase().includes(q) ?? false)
    );
  });

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="row-between">
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Investigations</h1>
          <p className="text-muted" style={{ margin: '4px 0 0' }}>
            Manage deviation records, source evidence, RCA runs, and CAPA actions
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setShowCreate(true)}
        >
          <Plus size={16} /> New Investigation
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card card-body">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: 420 }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }}
            />
            <input
              className="input"
              style={{ paddingLeft: 32 }}
              placeholder="Search by title, product, batch, or site..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <select
            className="select"
            style={{ width: 200 }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="draft">Draft</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          {loading ? (
            <div className="card-body text-muted">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="card-body text-muted">No matching investigations found.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Product</th>
                  <th>Batch</th>
                  <th>Site</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inv) => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: 600 }}>
                      <Link to={`/investigations/${inv.id}`}>{inv.title}</Link>
                    </td>
                    <td>{inv.product_name ?? '—'}</td>
                    <td className="mono text-sm">{inv.batch_number ?? '—'}</td>
                    <td>{inv.manufacturing_site ?? '—'}</td>
                    <td>
                      <StatusBadge value={inv.status} />
                    </td>
                    <td className="text-muted text-sm">
                      {new Date(inv.updated_at).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Link
                        to={`/investigations/${inv.id}`}
                        className="btn btn-secondary btn-sm"
                      >
                        Open
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
