import { useMemo } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type {
  CAPARecommendation,
  EvidenceItem,
  RCARunDetail,
} from '../types/api';

interface EvidenceGraphProps {
  investigationTitle: string;
  rcaRun: RCARunDetail | null;
  evidence: EvidenceItem[];
  capas: CAPARecommendation[];
}

export function EvidenceGraph({
  investigationTitle,
  rcaRun,
  evidence,
  capas,
}: EvidenceGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const builtNodes: Node[] = [];
    const builtEdges: Edge[] = [];

    builtNodes.push({
      id: 'inv-root',
      position: { x: 20, y: 180 },
      data: { label: `Investigation: ${investigationTitle.slice(0, 48)}` },
      style: {
        background: '#0f172a',
        color: '#ffffff',
        border: '2px solid #0284c7',
        borderRadius: 10,
        fontWeight: 600,
        fontSize: 12,
        padding: 10,
        width: 220,
      },
    });

    if (!rcaRun) {
      return { nodes: builtNodes, edges: builtEdges };
    }

    const evidenceById = new Map(evidence.map((e) => [e.id, e]));
    const placedEvidence = new Set<string>();
    let evRow = 0;

    rcaRun.hypotheses.forEach((hyp, idx) => {
      const hypNodeId = `hyp-${hyp.id}`;
      const hypY = 40 + idx * 170;

      const isConfirmed = hyp.status === 'confirmed_by_investigator';
      const isRejected = hyp.status === 'rejected' || hyp.status === 'contradicted';

      builtNodes.push({
        id: hypNodeId,
        position: { x: 320, y: hypY },
        data: {
          label: `H${idx + 1}: ${hyp.title.slice(0, 44)} [${hyp.status.replace(/_/g, ' ')}]`,
        },
        style: {
          background: isConfirmed ? '#dcfce7' : isRejected ? '#fee2e2' : '#fef3c7',
          color: '#0f172a',
          border: `2px solid ${isConfirmed ? '#16a34a' : isRejected ? '#dc2626' : '#d97706'}`,
          borderRadius: 10,
          fontSize: 12,
          fontWeight: 600,
          padding: 10,
          width: 240,
        },
      });

      builtEdges.push({
        id: `e-inv-${hyp.id}`,
        source: 'inv-root',
        target: hypNodeId,
        animated: hyp.status === 'proposed' || hyp.status === 'under_review',
        style: { stroke: '#64748b', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed },
      });

      hyp.evidence_links.forEach((link) => {
        const evNodeId = `ev-${link.evidence_item_id}`;
        if (!placedEvidence.has(link.evidence_item_id)) {
          placedEvidence.add(link.evidence_item_id);
          const ev = evidenceById.get(link.evidence_item_id);
          const snippet = ev
            ? ev.field_name
              ? `${ev.field_name}: ${ev.extracted_value}`
              : ev.content.slice(0, 52)
            : link.evidence_item_id.slice(0, 8);

          builtNodes.push({
            id: evNodeId,
            position: { x: 640, y: 20 + evRow * 95 },
            data: {
              label: `${ev?.evidence_kind === 'extracted_fact' ? 'Fact' : 'Source'}: ${snippet}`,
            },
            style: {
              background: '#f8fafc',
              color: '#0f172a',
              border: '1px solid #94a3b8',
              borderRadius: 8,
              fontSize: 11,
              padding: 8,
              width: 230,
            },
          });
          evRow += 1;
        }

        const edgeColor =
          link.relationship_type === 'supports'
            ? '#16a34a'
            : link.relationship_type === 'contradicts'
              ? '#dc2626'
              : '#64748b';

        builtEdges.push({
          id: `e-link-${link.id}`,
          source: hypNodeId,
          target: evNodeId,
          label: link.relationship_type,
          style: {
            stroke: edgeColor,
            strokeWidth: 2,
            strokeDasharray: link.relationship_type === 'contextual' ? '5 4' : undefined,
          },
          labelStyle: { fontSize: 10, fill: edgeColor, fontWeight: 600 },
          markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
        });
      });

      const hypCapas = capas.filter((c) => c.hypothesis_id === hyp.id);
      hypCapas.slice(0, 3).forEach((capa, cIdx) => {
        const capaNodeId = `capa-${capa.id}`;
        builtNodes.push({
          id: capaNodeId,
          position: { x: 940, y: hypY + cIdx * 82 },
          data: {
            label: `CAPA (${capa.capa_type}): ${capa.title.slice(0, 42)}`,
          },
          style: {
            background: '#e0f2fe',
            color: '#075985',
            border: '1.5px solid #0284c7',
            borderRadius: 8,
            fontSize: 11,
            fontWeight: 500,
            padding: 8,
            width: 230,
          },
        });
        builtEdges.push({
          id: `e-capa-${capa.id}`,
          source: hypNodeId,
          target: capaNodeId,
          style: { stroke: '#0284c7', strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#0284c7' },
        });
      });
    });

    return { nodes: builtNodes, edges: builtEdges };
  }, [investigationTitle, rcaRun, evidence, capas]);

  if (!rcaRun) {
    return (
      <div className="alert alert-info">
        Run an RCA analysis first to visualize the Investigation → Hypothesis → Evidence → CAPA graph.
      </div>
    );
  }

  return (
    <div style={{ height: 460, border: '1px solid var(--border)', borderRadius: 10, background: '#ffffff' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
