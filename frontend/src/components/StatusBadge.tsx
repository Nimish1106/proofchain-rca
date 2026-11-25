interface StatusBadgeProps {
  value: string;
}

const VARIANT_MAP: Record<string, string> = {
  // Evidence
  accepted: 'badge-success',
  rejected: 'badge-danger',
  pending: 'badge-warning',

  // Hypothesis
  proposed: 'badge-warning',
  under_review: 'badge-info',
  supported_by_records: 'badge-info',
  contradicted: 'badge-danger',
  confirmed_by_investigator: 'badge-success',

  // Gaps & Priority
  open: 'badge-warning',
  addressed: 'badge-success',
  waived: 'badge-neutral',
  high: 'badge-danger',
  critical: 'badge-danger',
  medium: 'badge-warning',
  low: 'badge-neutral',

  // Runs & Investigation
  completed: 'badge-success',
  running: 'badge-info',
  failed: 'badge-danger',
  draft: 'badge-neutral',
  in_progress: 'badge-info',
  in_review: 'badge-warning',
  approved: 'badge-success',

  // Why step basis
  source_supported: 'badge-success',
  hypothesis: 'badge-warning',
  unknown: 'badge-neutral',

  // CAPA type
  corrective: 'badge-info',
  preventive: 'badge-neutral',
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const variant = VARIANT_MAP[value] ?? 'badge-neutral';
  const label = value.replace(/_/g, ' ');
  return <span className={`badge ${variant}`}>{label}</span>;
}
