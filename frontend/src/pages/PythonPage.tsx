import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { PythonOutputDTO } from '../types/workflow';
import { CodeViewer } from '../components/CodeViewer';
import { Loader2 } from 'lucide-react';

interface PythonPageProps {
  analysisId: string;
}

export const PythonPage: React.FC<PythonPageProps> = ({ analysisId }) => {
  const [pythonData, setPythonData] = useState<PythonOutputDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getPython(analysisId)
      .then((data) => {
        if (mounted) {
          setPythonData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to fetch Python code.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [analysisId]);

  const handleDownload = () => {
    window.location.href = api.getDownloadUrl(analysisId, 'python');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
        <Loader2 size={28} color="#38bdf8" className="animate-spin" />
        <span style={{ color: '#94a3b8', fontSize: '14px' }}>Loading Python pipeline...</span>
      </div>
    );
  }

  if (error || !pythonData) {
    return (
      <div style={{ color: '#f87171', padding: '20px' }}>
        Failed to load Python code: {error}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1050px' }}>
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
          04 Python Pipeline Output
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.5px' }}>
          Executable pandas transformation script with line-level traceability
        </h1>
      </div>

      <CodeViewer pythonData={pythonData} onDownload={handleDownload} />
    </div>
  );
};
