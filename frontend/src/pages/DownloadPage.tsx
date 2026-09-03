import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { DownloadCard } from '../components/DownloadCard';
import { DocumentGenerationModal, ReportType } from '../components/DocumentGenerationModal';
import { FileText, FileCode2, Terminal, GitFork, Archive, Table, AlertCircle, X, Download } from 'lucide-react';

interface DownloadPageProps {
  analysisId: string;
}

export const DownloadPage: React.FC<DownloadPageProps> = ({ analysisId }) => {
  const [generatingReport, setGeneratingReport] = useState<ReportType | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showBundleModal, setShowBundleModal] = useState<boolean>(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showBundleModal) {
        setShowBundleModal(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showBundleModal]);

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

      {/* Complete Bundle Download Confirmation Modal */}
      {showBundleModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="bundle-modal-title"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(4px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            boxSizing: 'border-box',
          }}
          onClick={() => setShowBundleModal(false)}
        >
          <div
            style={{
              maxWidth: '460px',
              width: '100%',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-lg, 8px)',
              padding: '32px 28px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)',
              position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => setShowBundleModal(false)}
              aria-label="Close"
              style={{
                position: 'absolute',
                top: '14px',
                right: '14px',
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-sm, 4px)',
              }}
            >
              <X size={18} />
            </button>

            {/* Icon */}
            <div style={{ position: 'relative', marginBottom: '20px' }}>
              <div
                style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '16px',
                  background: 'var(--color-surface-secondary)',
                  border: '1.5px solid var(--color-primary-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-primary)',
                  boxShadow: '0 4px 14px rgba(0, 0, 0, 0.15)',
                }}
              >
                <Archive size={28} />
              </div>
            </div>

            {/* Brand Pre-title */}
            <div
              style={{
                fontSize: '10.5px',
                fontWeight: 800,
                letterSpacing: '1px',
                textTransform: 'uppercase',
                color: 'var(--color-primary)',
                marginBottom: '6px',
              }}
            >
              Complete Bundle Export
            </div>

            {/* Modal Title */}
            <h3
              id="bundle-modal-title"
              style={{
                fontSize: '18px',
                fontWeight: 800,
                color: 'var(--color-text)',
                margin: '0 0 10px 0',
                letterSpacing: '-0.2px',
              }}
            >
              Download Complete Bundle
            </h3>

            {/* Modal Description */}
            <p
              style={{
                fontSize: '13px',
                color: 'var(--color-text-secondary)',
                lineHeight: '1.5',
                margin: '0 0 24px 0',
              }}
            >
              Download all generated workflow artifacts (Source-to-Target Mapping, Tool Specifications, Business Report, Python pipeline, Workflow JSON, SVG diagram, and diagnostics) in a single ZIP archive.
            </p>

            {/* Action Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%', justifyContent: 'center' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowBundleModal(false)}
                style={{ flex: 1, padding: '9px 16px', fontSize: '13px' }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setShowBundleModal(false);
                  triggerDirectDownload('zip');
                }}
                style={{ flex: 1, padding: '9px 16px', fontSize: '13px' }}
              >
                <Download size={14} />
                <span>Download ZIP</span>
              </button>
            </div>
          </div>
        </div>
      )}

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
        onDownload={() => setShowBundleModal(true)}
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
