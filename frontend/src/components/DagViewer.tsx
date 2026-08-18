import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Download } from 'lucide-react';

interface DagViewerProps {
  svgContent: string;
  onDownloadDocx?: () => void;
}

export const DagViewer: React.FC<DagViewerProps> = ({ svgContent, onDownloadDocx }) => {
  const [zoom, setZoom] = useState(1);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.15, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.15, 0.5));
  const handleResetZoom = () => setZoom(1);

  return (
    <div
      className="glass-card"
      style={{
        overflow: 'hidden',
        position: 'relative',
        background: 'rgba(11, 17, 33, 0.95)',
        border: '1px solid rgba(51, 65, 85, 0.6)',
      }}
    >
      {/* Top Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
        background: 'rgba(15, 23, 42, 0.8)',
      }}>
        <div style={{ fontSize: '12px', fontWeight: '600', color: '#94a3b8' }}>
          Visual DAG — scroll or zoom to inspect workflow topology
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Zoom controls */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'rgba(30, 41, 59, 0.8)',
            borderRadius: '6px',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            padding: '2px',
          }}>
            <button
              onClick={handleZoomOut}
              title="Zoom out"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px 6px',
                borderRadius: '4px',
              }}
            >
              <ZoomOut size={14} />
            </button>
            <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#f8fafc', padding: '0 6px' }}>
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              title="Zoom in"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px 6px',
                borderRadius: '4px',
              }}
            >
              <ZoomIn size={14} />
            </button>
            <button
              onClick={handleResetZoom}
              title="Reset zoom"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px 6px',
                borderRadius: '4px',
              }}
            >
              <RotateCcw size={14} />
            </button>
          </div>

          {/* Download Word Doc Button */}
          {onDownloadDocx && (
            <button
              onClick={onDownloadDocx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '6px',
                background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                border: 'none',
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(168, 85, 247, 0.3)',
              }}
            >
              <Download size={13} />
              <span>Download Word Doc</span>
            </button>
          )}
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div style={{
        padding: '24px',
        overflow: 'auto',
        maxHeight: '450px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: 'top left',
            transition: 'transform 0.15s ease',
            width: '100%',
          }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      </div>
    </div>
  );
};
