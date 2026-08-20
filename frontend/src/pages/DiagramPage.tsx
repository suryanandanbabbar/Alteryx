import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DiagramDTO } from '../types/workflow';
import { DagViewer } from '../components/DagViewer';
import { NodeDetails } from '../components/NodeDetails';
import { Loader2, AlertCircle } from 'lucide-react';

interface DiagramPageProps {
  analysisId: string;
  selectedToolId?: number | null;
}

export const DiagramPage: React.FC<DiagramPageProps> = ({ analysisId, selectedToolId: initialSelectedToolId }) => {
  const [diagramData, setDiagramData] = useState<DiagramDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedToolId, setSelectedToolId] = useState<number | null>(initialSelectedToolId ?? null);

  useEffect(() => {
    if (initialSelectedToolId) {
      setSelectedToolId(initialSelectedToolId);
    }
  }, [initialSelectedToolId]);

  useEffect(() => {
    let mounted = true;
    api.getDiagram(analysisId)
      .then((data) => {
        if (mounted) {
          setDiagramData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to load workflow diagram.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [analysisId]);

  const handleDownloadSvg = () => {
    window.location.href = api.getDownloadUrl(analysisId, 'svg');
  };

  const handleSelectNode = (toolId: number) => {
    setSelectedToolId(toolId);
    const detailEl = document.getElementById(`tool-detail-${toolId}`);
    if (detailEl) {
      detailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
        <Loader2 size={24} color="var(--color-primary)" className="animate-spin" />
        <span style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading workflow diagram...</span>
      </div>
    );
  }

  if (error || !diagramData) {
    return (
      <div style={{
        padding: '16px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--color-error-subtle)',
        border: '1px solid rgba(220, 38, 38, 0.3)',
        color: 'var(--color-error)',
        fontSize: '13px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <AlertCircle size={16} />
        <span>Failed to load diagram: {error}</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', width: '100%' }}>
      {/* Section Subtitle */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1px',
          color: 'var(--color-primary)',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}>
          02 Workflow Diagram
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Interactive DAG & Tool Configurations
        </h2>
      </div>

      {/* Full-Width Interactive DAG Visualization */}
      <DagViewer
        svgContent={diagramData.svg}
        onDownloadSvg={handleDownloadSvg}
        onSelectNode={handleSelectNode}
        selectedToolId={selectedToolId}
      />

      {/* Node Configurations & Details */}
      <NodeDetails
        nodes={diagramData.nodes}
        selectedToolId={selectedToolId}
      />
    </div>
  );
};
