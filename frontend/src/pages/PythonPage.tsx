import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { PythonOutputDTO } from '../types/workflow';
import { CodeViewer } from '../components/CodeViewer';
import { Loader2, AlertCircle } from 'lucide-react';

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
        <Loader2 size={24} color="var(--color-primary)" className="animate-spin" />
        <span style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading Python pipeline...</span>
      </div>
    );
  }

  if (error || !pythonData) {
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
        <span>Failed to load Python: {error}</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1000px' }}>
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
          Python
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Python / Pandas Pipeline Translation
        </h2>
      </div>

      <CodeViewer pythonData={pythonData} onDownload={handleDownload} />
    </div>
  );
};
