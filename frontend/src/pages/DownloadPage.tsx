import React, { useState } from 'react';
import { api } from '../api/client';
import { DownloadCard } from '../components/DownloadCard';
import { DocumentGenerationModal, ReportType } from '../components/DocumentGenerationModal';
import { FileText, FileCode2, Terminal, GitFork, Archive, Table, AlertCircle } from 'lucide-react';

interface DownloadPageProps {
  analysisId: string;
}

export const DownloadPage: React.FC<DownloadPageProps> = ({ analysisId }) => {
  const [generatingReport, setGeneratingReport] = useState<ReportType | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownloadWithModal = async (type: 'docx' | 'tool-specifications' | 'sttm') => {
    if (generatingReport) return; // Prevent duplicate clicks
    setDownloadError(null);
    const reportType: ReportType = type === 'docx' ? 'business' : type === 'sttm' ? 'sttm' : 'tool-specifications';
    setGeneratingReport(reportType);

    try {
      await api.downloadFile(analysisId, type);
    } catch (err: any) {
      setDownloadError(err.message || 'Failed to generate document. Please try again.');
    } finally {
      setGeneratingReport(null);
    }
  };

  const triggerDirectDownload = (type: 'json' | 'python' | 'svg' | 'zip') => {
    window.location.href = api.getDownloadUrl(analysisId, type);
  };

  const isGenerating = generatingReport !== null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1400px', width: '100%', position: 'relative' }}>
      {/* Document Generation Loading Modal */}
      {generatingReport && <DocumentGenerationModal type={generatingReport} />}

      {/* Error Alert */}
      {downloadError && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'var(--color-error-subtle)',
          border: '1px solid rgba(220, 38, 38, 0.3)',
          color: 'var(--color-error)',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}>
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>{downloadError}</div>
        </div>
      )}

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
          Download
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--color-text)', letterSpacing: '-0.3px', margin: 0 }}>
          Export Generated Analysis Artifacts
        </h2>
      </div>

      {/* Primary Master Bundle Card (Section 17) */}
      <DownloadCard
        icon={Archive}
        title="Complete bundle"
        subtitle="All generated artifacts (JSON, Python, SVG, Business Report, Tool Specifications, STTM Excel, Diagnostics) in a single ZIP"
        formatBadge=".zip"
        isPrimary={true}
        disabled={isGenerating}
        onDownload={() => triggerDirectDownload('zip')}
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
           icon={Table}
           title="Source-to-Target Mapping"
           subtitle="Field-level data lineage workbook mapping source attributes and transformations to targets"
           formatBadge=".xlsx"
           disabled={isGenerating}
           onDownload={() => handleDownloadWithModal('sttm')}
         />

        <DownloadCard
          icon={Table}
          title="Tool Specifications"
          subtitle="Complete tool-by-tool workflow specification with LLM-generated role and data-flow explanations"
          formatBadge=".xlsx"
          disabled={isGenerating}
          onDownload={() => handleDownloadWithModal('tool-specifications')}
        />

        <DownloadCard
          icon={FileText}
          title="Business Report"
          subtitle="Executive business analysis report with purpose, methodologies, findings, conclusions, lineage, and workflow"
          formatBadge=".docx"
          disabled={isGenerating}
          onDownload={() => handleDownloadWithModal('docx')}
        />

        <DownloadCard
          icon={Terminal}
          title="Python pipeline"
          subtitle="Generated pandas workflow script with line-level traceability headers"
          formatBadge=".py"
          disabled={isGenerating}
          onDownload={() => triggerDirectDownload('python')}
        />

        <DownloadCard
          icon={FileCode2}
          title="Workflow JSON"
          subtitle="Machine-readable workflow representation with metadata and graph topology"
          formatBadge=".json"
          disabled={isGenerating}
          onDownload={() => triggerDirectDownload('json')}
        />

        <DownloadCard
          icon={GitFork}
          title="SVG diagram"
          subtitle="Standalone, scalable vector DAG visualization"
          formatBadge=".svg"
          disabled={isGenerating}
          onDownload={() => triggerDirectDownload('svg')}
        />
      </div>
    </div>
  );
};
