import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Download } from 'lucide-react';

interface DagViewerProps {
  svgContent: string;
  onDownloadDocx?: () => void;
  onDownloadSvg?: () => void;
}

export const DagViewer: React.FC<DagViewerProps> = ({ svgContent, onDownloadSvg }) => {
  const [zoom, setZoom] = useState(1);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.15, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.15, 0.4));
  const handleReset = () => setZoom(1);

  return (
    <div className="app-card" style={{ overflow: 'hidden' }}>
      {/* Viewer Header / Toolbar */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface-secondary)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-text)' }}>
            Workflow Graph (DAG)
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-mono)',
            padding: '2px 6px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          }}>
            Vector SVG
          </span>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Zoom Controls */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
          }}>
            <button
              onClick={handleZoomOut}
              aria-label="Zoom out"
              style={{
                padding: '6px 8px',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer',
                borderRight: '1px solid var(--color-border)',
              }}
            >
              <ZoomOut size={14} />
            </button>
            <span style={{
              padding: '4px 8px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-text-muted)',
            }}>
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              aria-label="Zoom in"
              style={{
                padding: '6px 8px',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer',
                borderLeft: '1px solid var(--color-border)',
              }}
            >
              <ZoomIn size={14} />
            </button>
          </div>

          <button
            onClick={handleReset}
            className="btn-secondary"
            style={{ padding: '6px 10px', fontSize: '12px' }}
            title="Reset Zoom"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          {onDownloadSvg && (
            <button
              onClick={onDownloadSvg}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              <Download size={13} />
              <span>Download SVG</span>
            </button>
          )}
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div style={{
        padding: '32px 24px',
        overflow: 'auto',
        maxHeight: '520px',
        minHeight: '260px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg)',
      }}>
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: 'center center',
            transition: 'transform 0.1s ease',
          }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      </div>
    </div>
  );
};
