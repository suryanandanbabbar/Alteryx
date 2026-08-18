import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { JsonViewer } from '../components/JsonViewer';
import { Loader2 } from 'lucide-react';

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
          setError(err.message || 'Failed to fetch JSON data.');
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
        <Loader2 size={28} color="#38bdf8" className="animate-spin" />
        <span style={{ color: '#94a3b8', fontSize: '14px' }}>Loading JSON schema...</span>
      </div>
    );
  }

  if (error || !jsonData) {
    return (
      <div style={{ color: '#f87171', padding: '20px' }}>
        Failed to load JSON: {error}
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
          03 Structured JSON Output
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.5px' }}>
          Machine-readable workflow graph and metadata
        </h1>
      </div>

      <JsonViewer data={jsonData} onDownload={handleDownload} />
    </div>
  );
};
