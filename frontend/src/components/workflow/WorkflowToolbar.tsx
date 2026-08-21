import React from 'react';
import {
  Search,
  Maximize2,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Download,
  FileJson,
  ChevronLeft,
  ChevronRight,
  ArrowRight,
  ArrowDown,
  X,
} from 'lucide-react';

interface WorkflowToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onClearSearch: () => void;
  matchCount: number;
  activeMatchIndex: number;
  onNextMatch: () => void;
  onPrevMatch: () => void;
  onFitView: () => void;
  onResetLayout: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  zoomLevel: number;
  direction: 'LR' | 'TB';
  onToggleDirection: () => void;
  onDownloadSvg?: () => void;
  onDownloadJson?: () => void;
}

export const WorkflowToolbar: React.FC<WorkflowToolbarProps> = ({
  searchQuery,
  onSearchChange,
  onClearSearch,
  matchCount,
  activeMatchIndex,
  onNextMatch,
  onPrevMatch,
  onFitView,
  onResetLayout,
  onZoomIn,
  onZoomOut,
  zoomLevel,
  direction,
  onToggleDirection,
  onDownloadSvg,
  onDownloadJson,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px',
        padding: '8px 12px',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md, 6px)',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
      }}
    >
      {/* Left: Search Bar & Match Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '260px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            padding: '4px 8px',
            gap: '6px',
            width: '240px',
          }}
        >
          <Search size={14} color="var(--color-text-muted)" />
          <input
            type="text"
            placeholder="Search tools by name, ID, type..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: '12px',
              color: 'var(--color-text)',
              width: '100%',
            }}
          />
          {searchQuery && (
            <button
              onClick={onClearSearch}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: '2px',
                color: 'var(--color-text-muted)',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Clear search"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {searchQuery && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: matchCount > 0 ? 'var(--color-text-secondary)' : 'var(--color-error)',
                fontFamily: 'var(--font-mono)',
                whiteSpace: 'nowrap',
              }}
            >
              {matchCount > 0 ? `${activeMatchIndex + 1}/${matchCount}` : '0 matches'}
            </span>

            {matchCount > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                <button
                  onClick={onPrevMatch}
                  style={{
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '3px',
                    padding: '2px 4px',
                    cursor: 'pointer',
                    color: 'var(--color-text)',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Previous match (Shift+Enter)"
                >
                  <ChevronLeft size={12} />
                </button>
                <button
                  onClick={onNextMatch}
                  style={{
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '3px',
                    padding: '2px 4px',
                    cursor: 'pointer',
                    color: 'var(--color-text)',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Next match (Enter)"
                >
                  <ChevronRight size={12} />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: Layout, Zoom, and Export Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        {/* Layout Orientation Toggle */}
        <button
          onClick={onToggleDirection}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            padding: '4px 8px',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--color-text)',
            cursor: 'pointer',
          }}
          title={`Scan direction ${direction === 'LR' ? 'Horizontal (Left-to-Right)' : 'Vertical (Top-to-Bottom)'}`}
        >
          {direction === 'LR' ? (
            <>
              <ArrowRight size={12} />
              <span>LR Layout</span>
            </>
          ) : (
            <>
              <ArrowDown size={12} />
              <span>TB Layout</span>
            </>
          )}
        </button>

        {/* Reset Layout */}
        <button
          onClick={onResetLayout}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            padding: '4px 8px',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--color-text)',
            cursor: 'pointer',
          }}
          title="Reset node positions to auto-layout"
        >
          <RotateCcw size={12} />
          <span>Reset</span>
        </button>

        {/* Fit to Screen */}
        <button
          onClick={onFitView}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            padding: '4px 8px',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--color-text)',
            cursor: 'pointer',
          }}
          title="Fit diagram to screen"
        >
          <Maximize2 size={12} />
          <span>Fit</span>
        </button>

        <div style={{ height: '16px', width: '1px', background: 'var(--color-border)' }} />

        {/* Zoom Controls */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm, 4px)',
            padding: '2px',
          }}
        >
          <button
            onClick={onZoomOut}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '3px 6px',
              cursor: 'pointer',
              color: 'var(--color-text)',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Zoom Out (-)"
          >
            <ZoomOut size={13} />
          </button>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              padding: '0 4px',
              color: 'var(--color-text-secondary)',
              minWidth: '38px',
              textAlign: 'center',
            }}
          >
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={onZoomIn}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '3px 6px',
              cursor: 'pointer',
              color: 'var(--color-text)',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Zoom In (+)"
          >
            <ZoomIn size={13} />
          </button>
        </div>

        <div style={{ height: '16px', width: '1px', background: 'var(--color-border)' }} />

        {/* Downloads */}
        {onDownloadSvg && (
          <button
            onClick={onDownloadSvg}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--color-surface-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-text)',
              cursor: 'pointer',
            }}
            title="Download static SVG workflow diagram"
          >
            <Download size={12} />
            <span>SVG</span>
          </button>
        )}

        {onDownloadJson && (
          <button
            onClick={onDownloadJson}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'var(--color-surface-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm, 4px)',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-text)',
              cursor: 'pointer',
            }}
            title="Download workflow JSON"
          >
            <FileJson size={12} />
            <span>JSON</span>
          </button>
        )}
      </div>
    </div>
  );
};
