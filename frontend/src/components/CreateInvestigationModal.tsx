import { useState, type FormEvent } from 'react';
import { X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../store';
import { createInvestigation } from '../store/investigationsSlice';

interface CreateInvestigationModalProps {
  onClose: () => void;
  onCreated?: (id: string) => void;
}

export function CreateInvestigationModal({
  onClose,
  onCreated,
}: CreateInvestigationModalProps) {
  const dispatch = useAppDispatch();
  const saving = useAppSelector((s) => s.investigations.saving);

  const [title, setTitle] = useState('');
  const [productName, setProductName] = useState('');
  const [productGrade, setProductGrade] = useState('');
  const [batchNumber, setBatchNumber] = useState('');
  const [site, setSite] = useState('');
  const [processStage, setProcessStage] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [affectedQuantity, setAffectedQuantity] = useState('');
  const [affectedUnit, setAffectedUnit] = useState('');
  const [description, setDescription] = useState('');
  const [containment, setContainment] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!title.trim()) {
      setError('Investigation title is required.');
      return;
    }

    try {
      const created = await dispatch(
        createInvestigation({
          title: title.trim(),
          product_name: productName.trim() || null,
          product_grade: productGrade.trim() || null,
          batch_number: batchNumber.trim() || null,
          manufacturing_site: site.trim() || null,
          process_stage: processStage.trim() || null,
          incident_date: incidentDate || null,
          affected_quantity: affectedQuantity ? Number(affectedQuantity) : null,
          affected_unit: affectedUnit.trim() || null,
          incident_description: description.trim() || null,
          immediate_containment: containment.trim() || null,
        }),
      ).unwrap();
      onClose();
      onCreated?.(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create investigation');
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-panel" style={{ maxWidth: 740 }}>
        <div className="card-header">
          <h3 className="card-title">New Quality Deviation Investigation</h3>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="card-body stack" style={{ overflowY: 'auto' }}>
          {error && <div className="alert alert-danger">{error}</div>}

          <div className="form-grid">
            <div className="form-field full">
              <label className="form-label">Investigation Title *</label>
              <input
                className="input"
                placeholder="e.g., Reactor R-204 Temperature Excursion During Crystallization"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label className="form-label">API Product Name</label>
              <input
                className="input"
                placeholder="e.g., Atorvastatin Calcium API"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Product Grade</label>
              <input
                className="input"
                placeholder="e.g., USP / EP"
                value={productGrade}
                onChange={(e) => setProductGrade(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Batch Number</label>
              <input
                className="input"
                placeholder="e.g., ATV-2026-041"
                value={batchNumber}
                onChange={(e) => setBatchNumber(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Manufacturing Site</label>
              <input
                className="input"
                placeholder="e.g., Site B — API Synthesis Block 3"
                value={site}
                onChange={(e) => setSite(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Process Stage</label>
              <input
                className="input"
                placeholder="e.g., Crystallization & Drying"
                value={processStage}
                onChange={(e) => setProcessStage(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Incident Date</label>
              <input
                type="date"
                className="input"
                value={incidentDate}
                onChange={(e) => setIncidentDate(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Affected Quantity</label>
              <input
                type="number"
                step="0.001"
                min="0.001"
                className="input"
                placeholder="e.g., 450"
                value={affectedQuantity}
                onChange={(e) => setAffectedQuantity(e.target.value)}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Affected Unit</label>
              <input
                className="input"
                placeholder="e.g., kg"
                value={affectedUnit}
                onChange={(e) => setAffectedUnit(e.target.value)}
              />
            </div>

            <div className="form-field full">
              <label className="form-label">Incident Description</label>
              <textarea
                className="textarea"
                rows={3}
                placeholder="Describe the observed deviation or OOS event..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="form-field full">
              <label className="form-label">Immediate Containment</label>
              <textarea
                className="textarea"
                rows={2}
                placeholder="e.g., Batch placed on QA hold; equipment tagged out."
                value={containment}
                onChange={(e) => setContainment(e.target.value)}
              />
            </div>
          </div>

          <div className="row" style={{ justifyContent: 'flex-end', marginTop: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Creating...' : 'Create Investigation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
