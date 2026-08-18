import React from 'react';
import { api } from '../api/client';
import { DownloadCard } from '../components/DownloadCard';
import { FileText, FileCode2, Terminal, Network, Archive } from 'lucide-react';

interface DownloadPageProps {
  analysisId: string;
}

export const DownloadPage: React.FC<DownloadPageProps> = ({ analysisId }) => {
  const triggerDownload = (type: 'docx' | 'json' | 'python' | 'svg' | 'zip') => {
    window.location.href = api.getDownloadUrl(analysisId, type);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '900px' }}>
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
          05 Download All Files
        </div>
        <h1 style={{ fontSize: '26px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.5px', marginBottom: '8px' }}>
          Download individual files or grab everything as a single ZIP
        </h1>
        <p style={{ fontSize: '13px', color: '#94a3b8' }}>
          Export deterministic analysis artifacts, executable pandas scripts, vector diagrams, and complete Word documentation.
        </p>
      </div>

      {/* 4 Download Cards matching Screenshot 6 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <DownloadCard
          icon={FileText}
          title="Word Document (.docx)"
          subtitle="Diagram + node details + metadata + lineage report"
          buttonText="Download"
          buttonGradient="linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)"
          onDownload={() => triggerDownload('docx')}
        />

        <DownloadCard
          icon={FileCode2}
          title="JSON Data (.json)"
          subtitle="Full DAG structure, snake_case metadata, tools & diagnostics"
          buttonText="Download"
          buttonGradient="linear-gradient(135deg, #0284c7 0%, #0369a1 100%)"
          onDownload={() => triggerDownload('json')}
        />

        <DownloadCard
          icon={Terminal}
          title="Python Pipeline (.py)"
          subtitle="Executable pandas script with lineage and traceability headers"
          buttonText="Download"
          buttonGradient="linear-gradient(135deg, #10b981 0%, #059669 100%)"
          onDownload={() => triggerDownload('python')}
        />

        <DownloadCard
          icon={Network}
          title="SVG Diagram (.svg)"
          subtitle="Standalone, scalable vector DAG visualization"
          buttonText="Download"
          buttonGradient="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
          onDownload={() => triggerDownload('svg')}
        />

        {/* Master ZIP Bundle Card */}
        <div style={{ marginTop: '12px' }}>
          <DownloadCard
            icon={Archive}
            title="Complete Bundle Archive (.zip)"
            subtitle="Contains all 5 artifacts (workflow.json, workflow.py, workflow.svg, workflow.docx, diagnostics.json)"
            buttonText="Download ZIP"
            buttonGradient="linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
            onDownload={() => triggerDownload('zip')}
          />
        </div>
      </div>
    </div>
  );
};
