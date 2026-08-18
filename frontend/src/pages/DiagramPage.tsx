import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DiagramDTO } from '../types/workflow';
import { DagViewer } from '../components/DagViewer';
import { NodeDetails } from '../components/NodeDetails';
import { Loader2 } from 'lucide-react';

interface DiagramPageProps {
  analysisId: string;
  selectedToolId?: number | null;
}

export const DiagramPage: React.FC<DiagramPageProps> = ({ analysisId, selectedToolId }) => {
  const [diagramData, setDiagramData] = useState<DiagramDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          setError(err.message || 'Failed to fetch diagram.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [analysisId]);

  const handleDownloadDocx = () => {
    window.location.href = api.getDownloadUrl(analysisId, 'docx');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
        <Loader2 size={28} color="#38bdf8" className="animate-spin" />
        <span style={{ color: '#94a3b8', fontSize: '14px' }}>Loading workflow diagram...</span>
      </div>
    );
  }

  if (error || !diagramData) {
    return (
      <div style={{ color: '#f87171', padding: '20px' }}>
        Failed to load diagram: {error}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '1050px' }}>
      {/* Section Header */}
      <div>
        <div style={{
          fontSize: '11px',
          fontWeight: '700',
          letterSpacing: '1.5px',
          color: '#38bdf8',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}>
          02 Workflow Diagram
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.5px' }}>
          Interactive DAG topology and tool configurations
        </h1>
      </div>

      {/* DAG Visualization */}
      <DagViewer
        svgContent={diagramData.svg}
        onDownloadDocx={handleDownloadDocx}
      />

      {/* Node Details (Expandable) */}
      <NodeDetails
        nodes={diagramData.nodes}
        selectedToolId={selectedToolId}
      />
    </div>
  );
};
