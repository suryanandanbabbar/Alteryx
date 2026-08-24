import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { JsonViewer } from '../components/JsonViewer';
import { Loader2, AlertCircle } from 'lucide-react';

interface JsonPageProps {
  analysisId: string;
}

export const JsonPage: React.FC<JsonPageProps> = ({ analysisId }) => {
  const [jsonData, setJsonData] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getJson(analysisId)
      .then((data) => {
        if (mounted) {
          setJsonData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to fetch JSON representation.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [analysisId]);

  const handleDownload = () => {
    window.location.href = api.getDownloadUrl(analysisId, 'json');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
        <Loader2 size={24} color="var(--color-primary)" className="animate-spin" />
        <span style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading JSON schema...</span>
      </div>
    );
  }

  if (error || !jsonData) {
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
        <span>Failed to load JSON: {error}</span>
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
          04 JSON
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Canonical Intermediate Representation
        </h2>
      </div>

      <JsonViewer data={jsonData} onDownload={handleDownload} />
    </div>
  );
};
