import React from 'react';
import { api } from '../api/client';
import { DownloadCard } from '../components/DownloadCard';
import { FileText, FileCode2, Terminal, GitFork, Archive } from 'lucide-react';

interface DownloadPageProps {
  analysisId: string;
}

export const DownloadPage: React.FC<DownloadPageProps> = ({ analysisId }) => {
  const triggerDownload = (type: 'docx' | 'json' | 'python' | 'svg' | 'zip') => {
    window.location.href = api.getDownloadUrl(analysisId, type);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '850px' }}>
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
          05 Download
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Export Generated Analysis Artifacts
        </h2>
      </div>

      {/* Primary Master Bundle Card (Section 17) */}
      <DownloadCard
        icon={Archive}
        title="Complete bundle"
        subtitle="All generated artifacts (JSON, Python, SVG, Word Doc, Diagnostics) in a single ZIP"
        formatBadge=".zip"
        isPrimary={true}
        onDownload={() => triggerDownload('zip')}
      />

      {/* Individual Artifacts List */}
      <div style={{
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '0.8px',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        marginTop: '8px',
      }}>
        Individual Artifacts
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <DownloadCard
          icon={FileCode2}
          title="Workflow JSON"
          subtitle="Machine-readable workflow representation with metadata and graph topology"
          formatBadge=".json"
          onDownload={() => triggerDownload('json')}
        />

        <DownloadCard
          icon={Terminal}
          title="Python pipeline"
          subtitle="Generated pandas workflow script with line-level traceability headers"
          formatBadge=".py"
          onDownload={() => triggerDownload('python')}
        />

        <DownloadCard
          icon={FileText}
          title="Word document"
          subtitle="Comprehensive workflow documentation report with embedded visual DAG"
          formatBadge=".docx"
          onDownload={() => triggerDownload('docx')}
        />

        <DownloadCard
          icon={GitFork}
          title="SVG diagram"
          subtitle="Standalone, scalable vector DAG visualization"
          formatBadge=".svg"
          onDownload={() => triggerDownload('svg')}
        />
      </div>
    </div>
  );
};
